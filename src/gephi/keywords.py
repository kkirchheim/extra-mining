# -*- coding: utf-8 -*-
"""
For Gephi, we need a node list that provides attributed for nodes, and a co-occurence matrix that provides
edge weights.

We also create topic related analysis here.
"""
import logging.config
import os
from collections import OrderedDict
from itertools import permutations

import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter

from db import Review
from utils import AcademicTitleCategory
import config
from constants import *
import utils

import click

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def create_co_occurrence_matrix(df, keywords) -> pd.DataFrame:
    """
    Calculates the co-occurence-matrix for the given keywords
    """
    # a dic of dicts, one dic per keyword, containing co-occurences with other dicts
    occurrences = OrderedDict((key, OrderedDict((key, 0) for key in keywords)) for key in keywords)

    documents = [keywords for keywords in df[Review.KEYWORDS]]

    # Find the co-occurrences:
    for index, lis in enumerate(documents):
        # logger.info(index)
        for i in range(len(lis)):
            for item in lis[:i] + lis[i + 1:]:
                if item == "Inklusive_Pädagogik":
                    print(f"Inklusive_Pädagogik -> {lis[i]}")
                elif item == "Kindertagesstätte":
                    print(f"Kindertagesstätte -> {lis[i]}")

                occurrences[lis[i]][item] += 1

    return occurrences


def extract_nodelist(df, previous=None):
    """
    TODO: this can probably done much simpler in pandas ...
    :return:
    """
    logger.info("Extracting keywords ...")

    # count keywords, genders, titles in reviews
    keyword_counter = Counter()
    gender_counter = Counter()
    title_counter = Counter()

    # Count by academic title and gender
    group_keyword_counter = {}
    for g in ALL_GENDERS:
        group_keyword_counter[g] = {}
        for t in AcademicTitleCategory:
            group_keyword_counter[g][t] = Counter()

    # count keywords title-wise
    title_keyword_counters = {title: Counter() for title in AcademicTitleCategory}

    # count keywords gender-wise
    gender_keyword_counter = {gender: Counter() for gender in ALL_GENDERS}

    # loop through all reviews and count
    for index, review in df.iterrows():
        keywords = review[Review.KEYWORDS]
        gender = review[Review.REVIEWER_GENDER]
        highest_title = review[Review.REVIEWER_HIGHEST_TITLE]

        if highest_title is None:
            logger.error(f"Highest title is None: {index}")

        gender_counter[gender] += 1
        title_counter[highest_title] += 1

        for keyword in keywords:
            if keyword == "":
                continue

            title_keyword_counters[highest_title][keyword] += 1
            gender_keyword_counter[gender][keyword] += 1
            keyword_counter[keyword] += 1

            group_keyword_counter[gender][highest_title][keyword] += 1

    n_keywords = len(keyword_counter.keys())
    logger.info(f"Keywords: {n_keywords}")

    group_f_ratio = max(gender_counter[GENDER_MALE] / sum(gender_counter.values()), 0.0001)

    logger.info(f"Group Female Ratio: {group_f_ratio}")
    # create dataframe
    nodes = []

    tkc = title_keyword_counters

    # total number of keywords
    total_keywords = sum(keyword_counter.values())
    logger.info(f"Total occurences: {total_keywords}")

    # find ratio of articles per keyword that have been written by females
    for keyword, count in keyword_counter.items():

        count_gender_f = gender_keyword_counter[GENDER_FEMALE][keyword]
        count_gender_m = gender_keyword_counter[GENDER_MALE][keyword]
        count_gender_u = gender_keyword_counter[GENDER_ELSE][keyword]

        count_title_p = tkc[AcademicTitleCategory.prof][keyword]
        count_title_d = tkc[AcademicTitleCategory.phd][keyword]
        count_title_m = tkc[AcademicTitleCategory.bachelor][keyword] + tkc[AcademicTitleCategory.master][keyword] + \
                        tkc[AcademicTitleCategory.diploma][keyword] + tkc[AcademicTitleCategory.magister][keyword]

        # bmdm_counter[keyword]
        count_title_o = tkc[AcademicTitleCategory.none][keyword] + tkc[AcademicTitleCategory.unknown][keyword]

        if count_gender_m + count_gender_f == 0:
            ratio = 0.5
            relative_ratio = 0
        else:
            ratio = count_gender_f / (count_gender_m + count_gender_f)
            relative_ratio = ratio / group_f_ratio  # pos if ratio is higher than usual

        node = dict()
        node[GEPHI_ID] = keyword
        node[GEPHI_LABEL] = keyword
        node["occurrences"] = count

        if previous is not None:
            previous_total_keywords = previous["occurrences"].sum()

            try:
                previous_count = previous.at[keyword, "occurrences"]
            except KeyError:
                previous_count = 1  # TODO: should be 0 ...

            node["growth"] = count - previous_count

            occurence_ratio = count / total_keywords
            previous_occurence_ratio = previous_count / previous_total_keywords

            # relative
            node["occurence_ratio"] = occurence_ratio
            node["growth_relative"] = occurence_ratio - previous_occurence_ratio

        node["female_count"] = count_gender_f
        node["male_count"] = count_gender_m
        node["unknown_count"] = count_gender_u
        node["female_ratio"] = ratio
        node["relative_female_ratio"] = relative_ratio

        # academic title stuff
        s = count_title_p + count_title_d + count_title_m + count_title_o
        node["prof_ratio"] = count_title_p / s
        node["phd_ratio"] = count_title_d / s
        node["master_ratio"] = count_title_m / s
        node["notitle_ratio"] = count_title_o / s

        for g in ALL_GENDERS:
            exclusive = [AcademicTitleCategory.master, AcademicTitleCategory.bachelor, AcademicTitleCategory.diploma,
                         AcademicTitleCategory.magister]
            exclusive_sum = 0

            for t in AcademicTitleCategory:
                group_keyword_count = group_keyword_counter[g][t][keyword] / keyword_counter[keyword]

                if t in exclusive:
                    exclusive_sum += group_keyword_count
                    continue
                key = f"{g}+{t}"

                node[key] = group_keyword_count

            key = f"{g}+Master"
            node[key] = exclusive_sum

        nodes.append(node)

    node_df = pd.DataFrame(nodes)
    node_df.set_index(GEPHI_ID, inplace=True)
    node_df.sort_values("occurrences", ascending=False, inplace=True)
    return node_df


def get_unique_keywords(df):
    return df[Review.KEYWORDS].explode().dropna().unique()


#def repl(x):
#    return [w.replace(" ", "_") for w in x]

@click.command()
@click.option("--file", "-f", "path", type=click.Path(), default=None)
@click.option("--time-slice/--no-time-slice", "-t", "time_slice", default=False, is_flag=True)
@click.option("--group-slice/--no-group-slice", "-g", "group_slice", default=False, is_flag=True)
def main(path, time_slice, group_slice):
    """
    Creates the keyword co occurence matrix and a list of keywords, ordered by count
    :return:
    """
    if not path:
        path = os.path.join(config.DIR_PROCESSED, "reviews.pkl")

    logger.info(f"Reading '{path}'")
    df = pd.read_pickle(path)
    df = utils.default_df_filter(df)

    # df[Review.KEYWORDS] = df[Review.KEYWORDS].apply(repl)
    df.set_index(keys=Review.DATE, inplace=True)
    logger.info(f"Reviews: {len(df)}")

    # select time slice
    if time_slice:
        groups = utils.default_date_split(df)
    elif group_slice:
        groups = utils.default_group_split(df)
    else:
        groups = [("all-time", df)]

    previous = None
    topic_data = []
    cooc_data = []

    for group_name, group in groups:
        # determine output path
        logger.info(f"Timeslice: {group_name}")
        logger.info(f"Articles: {len(group)}")

        if time_slice:
            time_slice_name = "5Y"
            name = f"keywords-{time_slice_name}-{str(group_name).replace(' ', '-')}-nodelist.csv"
            nodelist_path = os.path.join(config.DIR_PROCESSED, name)
            name = f"keywords-{time_slice_name}-{str(group_name).replace(' ', '-')}-cooc-matrix.csv"
            cooc_path = os.path.join(config.DIR_PROCESSED, name)
        elif group_slice:
            name = f"keywords-{str(group_name).replace(' ', '-')}-nodelist.csv"
            nodelist_path = os.path.join(config.DIR_PROCESSED, name)
            name = f"keywords-{str(group_name).replace(' ', '-')}-cooc-matrix.csv"
            cooc_path = os.path.join(config.DIR_PROCESSED, name)
        else:
            nodelist_path = os.path.join(config.DIR_PROCESSED, f"keywords-nodelist.csv")
            cooc_path = os.path.join(config.DIR_PROCESSED, f"keywords-cooc-matrix.csv")

        # create nodelist df
        node_df = extract_nodelist(group, previous)
        previous = node_df.copy()

        # evaluate topics over time
        total_keyword_count = node_df["occurrences"].sum()
        for name, words in config.topic_clusters.items():
            topic_entry = {"name": name, "date": group_name}

            topic_counts = []

            for word in words:
                try:
                    count = node_df.at[word, "occurrences"]
                except:
                    count = 0

                topic_counts.append(count)

            topic_entry["ratio"] = sum(topic_counts) / total_keyword_count
            print(topic_entry)
            topic_data.append(topic_entry)

        # save nodelists
        utils.save_gephi_csv(node_df, nodelist_path)

        nodelist_path_pkl = nodelist_path.replace(".csv", ".pkl")
        logger.info(f"Writing nodelist to '{nodelist_path_pkl}'")
        node_df.to_pickle(nodelist_path_pkl)

        # create co-occurrence matrix
        logger.info("Creating co occurence matrix...")
        keywords = get_unique_keywords(group)
        logger.info(f"Number of unique keywords {len(keywords)}")
        occurrences = create_co_occurrence_matrix(group, keywords)

        logger.info("Creating dataframe ...")
        co_occur = pd.DataFrame.from_dict(occurrences)

        # we want to watc hseveral co occurecnes
        words = ["Schule", "Inklusion", "Kindertagesstätte", "Jugendhilfe", "Inklusive Pädagogik"]
        # words = ["Management", "Qualitätsmanagement", "Krankenhaus", "Altenpflege", "Gesundheitswesen", "Sozialeinrichtung"]

        for w1, w2 in permutations(words, 2):

            try:
                o = co_occur[w1][w2] / len(node_df)
            except KeyError:
                o = 0

            cooc_entry = {"date": group_name, "word1": w1, "word2": w2, "value": o}
            cooc_data.append(cooc_entry)
            logger.info(f"{w1} + {w2} -> {o}")

        # save co-occurrence matrix
        utils.save_gephi_csv(co_occur, cooc_path)

    # save topic data
    df = pd.DataFrame(topic_data)
    topic_data_path = os.path.join(config.DIR_PROCESSED, "topics.csv")
    df.to_csv(topic_data_path)

    df = pd.DataFrame(cooc_data)
    topic_data_path = os.path.join(config.DIR_PROCESSED, "cooc_topics-1.csv")
    df.to_csv(topic_data_path)

    logger.info("Done")
    # plt.show()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
