# -*- coding: utf-8 -*-
"""
Gather information about authors
"""
import logging.config
import os
import pandas as pd
import config
from db import Author, Review
from collections import Counter

import utils
import constants
from dnb import DNBConnector

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main(min_keyword_mentions=2):
    path = os.path.join(config.DIR_PROCESSED, "reviews-extended.pkl")
    df = pd.read_pickle(path)

    df = df.explode(Review.AUTHORS_ID)
    grouper = pd.Grouper(key=Review.AUTHORS_ID)
    groups = df.groupby(grouper)

    dnb = DNBConnector(config.load_secret_dnb())

    data = []

    for identifier, group in groups:

        persons = dnb.query_authority(identifier)
        if len(persons) > 1:
            logger.warning(f"More than 1: '{identifier}'")
            for person in persons:
                logger.warning(person.identifier())

        person = persons[0]

        counter = Counter()

        for keywords in group[Review.KEYWORDS]:
            for keyword in keywords:
                counter[keyword] += 1

        # filter reviewers with less than 'min_keyword_mentions' keyword mentions
        filtered_counter = counter.copy()

        for keyword, count in counter.items():
            if count >= min_keyword_mentions:
                del filtered_counter[keyword]

        if len(filtered_counter) == 0:
            continue

        # assemble entry
        entry = dict()
        entry[constants.GEPHI_ID] = identifier
        entry[constants.GEPHI_LABEL] = person.name()
        entry[Author.NAME] = person.name()
        entry[Author.TITLE] = person.title()
        entry[Author.AFFILIATION] = person.affiliations()
        entry[Author.REVIEWS_COUNT] = group[Review.DNB_ID].count()
        entry[Author.REVEWER_COUNT] = group[Review.REVIEWER_NAME].count()
        entry[Author.PAGE_SUM] = group[Review.PAGES].sum()
        entry[Author.KEYWORDS] = list(filtered_counter.keys())
        entry[Author.KEYWORD_COUNT] = len(filtered_counter.values())
        entry[Author.KEYOWRD_COUNTS] = list(filtered_counter.values())

        logger.info(f"{entry[Author.NAME]}, {entry[Author.REVIEWS_COUNT]}")

        data.append(entry)

    df2 = pd.DataFrame(data)
    df2.set_index(keys=constants.GEPHI_ID, inplace=True)
    df2.sort_values(by=Author.REVIEWS_COUNT, inplace=True, ascending=False)
    logger.info(df2)

    out_path = os.path.join(config.DIR_PROCESSED, "authors.pkl")
    df2.to_pickle(out_path)

    out_path = os.path.join(config.DIR_PROCESSED, "authors.csv")
    utils.save_gephi_csv(df2, out_path)

    cooc_matrix = utils.dict_create_co_occurence_matrix(data, self_loops=False)
    path = os.path.join(config.DIR_PROCESSED, "authors-cooc.csv")
    utils.save_gephi_csv(cooc_matrix, path)


if __name__ == '__main__':
    main()
