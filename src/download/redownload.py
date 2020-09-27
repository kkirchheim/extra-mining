# -*- coding: utf-8 -*-
"""
Redownload all articles that could not be processed
"""

import pandas as pd
import logging.config
import os
import time

from .download import scrape, save
import config
from db import Review
import click

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--sleep", "-s", "sleep", type=float, default=1.0)
@click.option("--output", "-o", "output", type=click.Path(), default=config.DIR_RAW_HTML)
def main(sleep, output):
    """
    redownload all reviews for wich the parsing failed.
    :param sleep: 
    :param output: 
    :return: 
    """
    logger.info("Sleep: %f", sleep)

    reviews_path = os.path.join(config.DIR_PROCESSED, "reviews.csv")
    df = pd.read_csv(reviews_path, encoding="utf-16")

    df = df[[Review.ID, Review.PARSED_SUCCESS]]
    df = df[~df[Review.PARSED_SUCCESS]]
    logger.info(len(df))

    for index, row in df.sample(frac=1).iterrows():
        identifier = row[Review.ID]
        logger.info("Scraping %d", identifier)
        content = scrape(config.URL_WEBSITE, identifier)
        path = os.path.join(output, f"{identifier}.html")
        save(path, content)
        time.sleep(sleep)

    logger.info("Done.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
