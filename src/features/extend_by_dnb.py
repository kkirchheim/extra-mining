# -*- coding: utf-8 -*-
"""
Scrapes information from the dnb and adds it to the reviews.pkl file. Using this is optional, however it will most
likely improve the obtained results as it fills missing values.
"""
import logging.config
import os
import pandas as pd
import config
import utils
from db import Review
from config import load_secret_dnb
from dnb import DNBConnector

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main():
    dnb = DNBConnector(load_secret_dnb())

    path = os.path.join(config.DIR_PROCESSED, "reviews.pkl")
    df = pd.read_pickle(path)

    df = utils.default_df_filter(df)
    df = df[~df[Review.ISBN].isna()]

    logger.info(len(df))
    df.set_index(keys=Review.ID, inplace=True)

    entries = []

    for n, (index, row) in enumerate(df.iterrows()):
        isbn = row[Review.ISBN]
        if isbn is None:
            continue

        logger.info(f"{n} -> '{isbn}'")
        books = dnb.query_bibliography(isbn)

        publisher = None
        year = None
        authors_name = []
        authors_profession = []
        authors_country = []
        authors_affiliations = []
        authors_id = []
        dnb_id = None

        if len(books) == 0:
            logger.warning(f"No book found for isbn '{isbn}'")

        else:
            book = books[0]
            publisher = book.publisher()
            year = book.publishing_year()
            dnb_id = book.identifier()

            ids = []
            ids.extend(book.authors())
            ids.extend(book.contributors())
            ids.extend(book.editors())

            for identifier in ids:
                authorities = dnb.query_authority(identifier)
                if len(authorities) == 0:
                    logger.error(f"Did not found authority for id '{identifier}'")
                    continue

                person = authorities[0]
                authors_name.append(person.name())
                authors_profession.append(person.profession())
                authors_country.append(person.country_code())
                authors_affiliations.append(person.affiliations())
                authors_id.append(person.identifier())

        entry = dict()
        entry[Review.ID] = index
        entry[Review.ISBN] = isbn
        entry[Review.PUBLISHER] = publisher
        entry[Review.PUBLISHED_YEAR] = year
        entry[Review.AUTHORS_AFFILIATIONS] = authors_affiliations
        entry[Review.AUTHORS_COUNTRY] = authors_country
        entry[Review.AUTHORS_NAME] = authors_name
        entry[Review.AUTHORS_PROFESSION] = authors_profession
        entry[Review.AUTHORS_ID] = authors_id
        entry[Review.DNB_ID] = dnb_id

        entries.append(entry)

    df2 = pd.DataFrame(entries)
    df2.set_index(keys=Review.ID, inplace=True)

    cols_to_drop = list(entries[0].keys())
    cols_to_drop.remove(Review.ID)

    df = df.drop(cols_to_drop, axis=1)
    result: pd.DataFrame = pd.concat([df, df2], axis=1).reindex(df.index)

    logger.info(result)
    result.reset_index(inplace=True)

    # Override
    path_out = os.path.join(config.DIR_PROCESSED, "reviews.csv")
    utils.save_gephi_csv(result, path_out)

    path_out = os.path.join(config.DIR_PROCESSED, "reviews.pkl")
    result.to_pickle(path_out)


if __name__ == '__main__':
    main()
