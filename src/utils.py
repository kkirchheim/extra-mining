# -*- coding: utf-8 -*-
"""

"""
import time
import multiprocessing as mp
import config
import logging
from collections import OrderedDict
import pandas as pd
import enum
import numpy as np
import functools
import csv

from db import Review
from constants import *

logger = logging.getLogger(__name__)


def save_gephi_csv(df, path):
    """Stores dataframe as CSV in a format readable by gephi"""
    logger.info(f"Saving to {path}")
    df.to_csv(path, sep=";", quoting=csv.QUOTE_ALL)


def default_df_filter(df):
    print(f"Datafram initial len: {len(df)}")
    df: pd.DataFrame = df[df[Review.PARSED_SUCCESS]]
    df = df[df[Review.DATE] < config.enddate]
    df = df[df[Review.DATE] > config.startdate]
    print(f"Datafram -date len: {len(df)}")

    # filter dipl. päd. jos schnurer
    df = df[df[Review.REVIEWER_ID] != 34346]
    print(f"Datafram -authors len: {len(df)}")
    return df


def default_date_split(df):
    """
    Apply 5 years split
    Parameters
    ----------
    df

    Returns
    -------

    """
    df2 = df.reset_index()

    ranges = [
        (np.datetime64("2001-01-01"), np.datetime64("2002-12-31")),
        (np.datetime64("2003-01-01"), np.datetime64("2004-12-31")),
        (np.datetime64("2005-01-01"), np.datetime64("2006-12-31")),
        (np.datetime64("2007-01-01"), np.datetime64("2008-12-31")),
        (np.datetime64("2009-01-01"), np.datetime64("2010-12-31")),
        (np.datetime64("2011-01-01"), np.datetime64("2012-12-31")),
        (np.datetime64("2013-01-01"), np.datetime64("2014-12-31")),
        (np.datetime64("2015-01-01"), np.datetime64("2016-12-31")),
        (np.datetime64("2017-01-01"), np.datetime64("2018-12-31"))
        ]

    values = []

    for date_low, date_high in ranges:
        tmp = df2[df2[Review.DATE] >= date_low]
        tmp = tmp[tmp[Review.DATE] <= date_high]

        # create pretty name for the group
        group_name = f"{date_low.astype(object).year}-{date_high.astype(object).year}"
        values.append((group_name, tmp.copy()))

    return values


def default_title_split(df):
    values = []

    df_prof = df[df[Review.REVIEWER_HIGHEST_TITLE] == AcademicTitleCategory.prof]
    values.append((AcademicTitleCategory.prof, df_prof))

    df_phd = df[df[Review.REVIEWER_HIGHEST_TITLE] == AcademicTitleCategory.phd]
    values.append((AcademicTitleCategory.phd, df_phd))

    master_eqiv = [AcademicTitleCategory.magister, AcademicTitleCategory.master, AcademicTitleCategory.diploma]
    df_master = df[df[Review.REVIEWER_HIGHEST_TITLE].isin(master_eqiv)]
    values.append((AcademicTitleCategory.master, df_master))

    other_titles = [AcademicTitleCategory.none, AcademicTitleCategory.unknown]
    df_other = df[df[Review.REVIEWER_HIGHEST_TITLE].isin(other_titles)]
    values.append((AcademicTitleCategory.unknown, df_other))

    return values


def default_group_split(df):
    """
    Split by Gender and Highest academic title
    Parameters
    ----------
    df

    Returns
    -------

    """
    df2 = df.reset_index()

    groups = {}

    for gender in ALL_GENDERS:
        split = df2[df2[Review.REVIEWER_GENDER] == gender]

        for name, group in default_title_split(split):
            groups[f"{gender}-{name}"] = group

    return zip(groups.keys(), groups.values())


class EtaCounter:
    """
    Thread safe counter to estimate the ETA
    """

    def __init__(self, count):
        self.count = count
        self._t_start = None
        self._current = None
        self._lock = mp.RLock()

    def start(self):
        self._t_start = time.time()
        self._current = 0

    def next(self):
        self._lock.acquire()
        self._current += 1
        eta = self.get_eta()
        self._lock.release()
        return eta

    def get_current(self):
        return self._current

    def get_t_mean(self):
        return (time.time() - self._t_start) / self._current

    def get_eta(self):
        return (self.count - self._current) * self.get_t_mean()

    def get_limit(self):
        return self.count

    def get_pretty_eta(self):
        return sec2time(self.get_eta())


@functools.total_ordering
class AcademicTitleCategory(enum.Enum):
    """
    Academic Title. Implemented as enum so we have ordering.
    """
    prof = 7
    phd = 6
    magister = 5
    diploma = 4
    master = 3
    bachelor = 2
    unknown = 1
    none = 0

    def __str__(self):
        mapping = {
            AcademicTitleCategory.prof: "Professor",
            AcademicTitleCategory.phd: "Doktor",
            AcademicTitleCategory.diploma: "Diplom",
            AcademicTitleCategory.master: "Master",
            AcademicTitleCategory.magister: "Magister",
            AcademicTitleCategory.bachelor: "Bachelor",
            AcademicTitleCategory.none: "No-Title",
            AcademicTitleCategory.unknown: "Unbekannt"
        }
        return mapping[self]

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value

        return NotImplemented

    @staticmethod
    def get_highest(titles):
        if titles is None or len(titles) == 0:
            return AcademicTitleCategory.none
        else:
            return max(titles)


def clean_html_text(t):
    t = t.replace("\n", "")
    t = t.replace("\t", "")
    t = ' '.join(t.split())
    return t


def load_list(path):
    li = []
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s.startswith("#"):
                continue

            li.append(s)

    return li


def get_ignore_urls():
    return load_list(config.PATH_IGNORE_URLS)


def get_german_cities():
    return load_list(config.PATH_CITIES)


def get_stop_words():
    return load_list(config.PATH_STOP_WORDS)


def sec2time(sec, n_msec=0):
    """
    Convert seconds to 'D days, HH:MM:SS.FFF

    :param sec:
    :param n_msec:
    :return:
    """

    if hasattr(sec, '__len__'):
        return [sec2time(s) for s in sec]
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if n_msec > 0:
        pattern = '%%02d:%%02d:%%0%d.%df' % (n_msec + 3, n_msec)
    else:
        pattern = r'%02d:%02d:%02d'
    if d == 0:
        return pattern % (h, m, s)
    return ('%d days, ' + pattern) % (d, h, m, s)


def df_create_co_occurence_matrix(df, keywords) -> pd.DataFrame:
    """
    Calculates the co-occurence-matrix for the given keywords
    """
    # a dic of dicts, one dic per keyword, containing co-occurences with other dicts
    occurrences = OrderedDict((key, OrderedDict((key, 0) for key in keywords)) for key in keywords)

    document_array = [doc for doc in df[Review.KEYWORDS]]

    # Find the co-occurrences:
    for document in document_array:
        for i in range(len(document)):
            for item in document[:i] + document[i + 1:]:
                if document[i] in keywords and item in keywords:
                    occurrences[document[i]][item] += 1

    logger.info("Creating dataframe...")
    co_occur = pd.DataFrame.from_dict(occurrences)

    return co_occur


def dict_create_co_occurence_matrix(data, self_loops=False) -> pd.DataFrame:
    """
    Calculates the co-occurence-matrix for the given keywords, given as a list of dicts
    """
    reviewers = [reviewer[GEPHI_ID] for reviewer in data]
    keywords = [reviewer[Review.KEYWORDS] for reviewer in data]

    # a dic of dicts, one dic per keyword, containing co-occurences with other dicts
    occurrences = OrderedDict(
        (reviewer, OrderedDict((reviewer, 0) for reviewer in reviewers)) for reviewer in reviewers)

    for r, reviewer in enumerate(reviewers):
        for c, reviewer2 in enumerate(reviewers):

            if not self_loops and c == r:
                continue

            keys = keywords[r]
            keys2 = keywords[c]

            # logger.info(reviewer)
            for key in keys:
                if key in keys2:
                    occurrences[reviewer][reviewer2] += 1

    return occurrences