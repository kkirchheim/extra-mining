# -*- coding: utf-8 -*-
"""
Determine which reviewer works on which topic
"""
import logging.config

import pandas as pd
import os
from collections import Counter

import click
import csv
import config
import utils
from db import Review, Reviewer
import constants

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def create_nodelist(groups, min_keyword_mentions):
    node_list = []

    # loop through reviewers (with unique id)
    for reviewer_id, group in groups:

        node = {}

        # count keywords
        reviewer_keywords = Counter()
        for keywords in group[Review.KEYWORDS]:
            for keyword in keywords:
                reviewer_keywords[keyword] += 1

        # filter reviewers with less than 'min_keyword_mentions' keyword mentions
        reviewer_keywords_filtered = {}

        for keyword, count in reviewer_keywords.items():
            if count >= min_keyword_mentions:
                reviewer_keywords_filtered[keyword] = count

        if len(reviewer_keywords_filtered) == 0:
            continue

        # guess reviewers location
        locations = group[Review.REVIEWER_LOCATION].values[0]  # take the first mentioned location
        if locations and len(locations) > 0:
            location = locations[0]
        else:
            location = "unknown"

        # get date of first and last published article
        dates = group.sort_values(by=f"{Review.DATE}_tmp", ascending=True)[f"{Review.DATE}_tmp"].values

        first_review_date = dates[0]
        latest_review_date = dates[len(dates) - 1]

        node[constants.GEPHI_ID] = reviewer_id
        node[Review.REVIEWER_ID] = reviewer_id
        node[constants.GEPHI_LABEL] = group[Review.REVIEWER_NAME].values[0]
        node[Reviewer.NAME] = group[Review.REVIEWER_NAME].values[0]
        node[Reviewer.TITLES] = group[Review.REVIEWER_TITLE].values[0]
        node[Reviewer.HIGHEST_TITLE] = utils.AcademicTitleCategory.get_highest(node[Reviewer.TITLES])

        node[Reviewer.KEYWORDS] = list(reviewer_keywords_filtered.keys())
        node[Reviewer.REVIEW_COUNT] = group[Review.ID].count()
        node[Reviewer.KEYWORD_COUNT] = len(reviewer_keywords_filtered)  # number of unique keywords
        node[Reviewer.KEYWORDS_COUNT] = list(reviewer_keywords_filtered.values())  # count for each unique keyword
        node[Reviewer.LOCATION] = location
        node[Reviewer.GENDER] = group[Review.REVIEWER_GENDER].values[0]
        node[Reviewer.PAGE_SUM] = group[Review.PAGES].sum()
        node[Reviewer.PAGE_MEAN] = group[Review.PAGES].mean()

        node[Reviewer.WORD_SUM] = group[Review.WORD_COUNT].sum()
        node[Reviewer.WORD_MEAN] = group[Review.WORD_COUNT].mean()
        node[Reviewer.FIRST_REVIEW_DATE] = first_review_date
        node[Reviewer.LATEST_REVIEW_DATE] = latest_review_date

        logger.debug(
            f"Reviewer ID: {reviewer_id}, "
            f"Reviews: {node[Reviewer.REVIEW_COUNT]:05d}, "
            f"Title: {node[Reviewer.HIGHEST_TITLE]}, "
            f"Keywords: ({reviewer_keywords_filtered})")

        node_list.append(node)

    return node_list


@click.command()
@click.option("--time-slice/--no-time-slice", "-t", "time_slice", default=False, is_flag=True)
@click.option("--min-keywords", "-k", "min_keyword_mentions", default=1)
def main(time_slice,
         min_keyword_mentions=1,
         ):
    path = os.path.join(config.DIR_PROCESSED, "reviews.pkl")
    logger.info(f"Reading '{path}'")
    df = pd.read_pickle(path)
    df = utils.default_df_filter(df)

    # copy date column
    date_tmp = df[Review.DATE].rename(f"{Review.DATE}_tmp")
    df[f"{Review.DATE}_tmp"] = date_tmp.values

    df = df.set_index(keys=Review.DATE)

    logger.info(f"Entries: {len(df)}")
    logger.info(df)
    # select time slice
    if time_slice:
        groups = utils.default_date_split(df)
    else:
        groups = [("all-time", df)]

    for date, time_group in groups:
        logger.info(f"Date Interval: {date}")
        grouper = pd.Grouper(key=Review.REVIEWER_ID)
        id_groups = time_group.groupby(grouper)

        node_list = create_nodelist(id_groups, min_keyword_mentions)

        df_out = pd.DataFrame(node_list)
        df_out.set_index(keys=constants.GEPHI_ID, inplace=True)
        df_out.sort_values(by=Reviewer.REVIEW_COUNT, ascending=False, inplace=True)

        if time_slice:
            time_slice_name = "5Y"
            name = f"reviewers-{time_slice_name}-{str(date).replace(' ', '-')}-nodelist.csv"
            nodelist_path = os.path.join(config.DIR_PROCESSED, name)
            name = f"reviewers-{time_slice_name}-{str(date).replace(' ', '-')}-cooc-matrix.csv"
            cooc_path = os.path.join(config.DIR_PROCESSED, name)
        else:
            nodelist_path = os.path.join(config.DIR_PROCESSED, f"reviewers-nodelist.csv")
            cooc_path = os.path.join(config.DIR_PROCESSED, f"reviewers-cooc-matrix.csv")

        utils.save_gephi_csv(df_out, nodelist_path)

        nodelist_path_pkl = nodelist_path.replace(".csv", ".pkl")
        logger.info(f"Saving to '{nodelist_path_pkl}'")
        df_out.to_pickle(nodelist_path_pkl)

        logger.info("Creating co-occurence matrix ... ")
        occurrences = utils.dict_create_co_occurence_matrix(node_list)
        logger.info("Creating dataframe...")
        co_occur = pd.DataFrame.from_dict(occurrences)
        utils.save_gephi_csv(co_occur, cooc_path)


if __name__ == "__main__":
    main()
