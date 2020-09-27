# -*- coding: utf-8 -*-
"""
Evaluate publisher, number of pages, price etc. of reviewed books
"""
import logging.config
import os

import matplotlib.pyplot as plt
import pandas as pd
import utils
import seaborn as sb

from db import Review

import config

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def eval_over_time(df, key):
    grouper = pd.Grouper(freq=key)
    groups = df.groupby(grouper)

    dates = []
    pages_mean = []
    price_mean = []
    count = []

    for date, gp in groups:
        dates.append(date)
        count.append(len(gp))
        pages_mean.append(gp[Review.PAGES].mean())
        # TODO price unit!
        price_mean.append(gp[gp[Review.PRICE_UNIT] == "EUR"][Review.PRICE].mean())
        logger.info(gp[Review.PAGES].mean())

    logger.info(dates)
    logger.info(pages_mean)

    sb.set()

    plt.figure()
    plt.plot(dates, pages_mean, label="Mean Pages")
    plt.plot(dates, count, label="Count")
    plt.legend()

    plt.figure()
    plt.plot(dates, price_mean, label="Mean Price")
    plt.legend()
    plt.tight_layout()

    out = os.path.join(config.DIR_REPORT, "books-ot.svg")
    plt.savefig(out, dpi=300)
    plt.close()


def eval_publishers_ranking(df, top_n=10):
    grouper = pd.Grouper(key=Review.PUBLISHER)
    groups = df.groupby(grouper)

    logger.info(f"{len(groups)}")
    data = dict()

    for publisher, group in groups:
        n = len(group)
        logger.info(f"{publisher} -> {n}")
        data[publisher] = len(group)

    top_keys_values = sorted(data.items(), key=lambda x: x[1], reverse=True)
    top_keys = [key for key, value in top_keys_values]
    top_values = [value for key, value in top_keys_values]

    publishers = []
    counts = []

    for publisher, count in zip(top_keys[:top_n], top_values[:top_n]):
        logger.info(f"{publisher} & {count} \\\\")
        publishers.append(publisher)
        counts.append(count)

    fig = plt.figure(figsize=(20, 10))
    plt.barh(publishers, counts, align='center', color="C0")
    plt.title("Publisher Ranking")
    plt.xlabel('Anzahl Reviews')
    plt.ylabel('Publisher')
    plt.tight_layout()

    out = os.path.join(config.DIR_REPORT, "top-publishers.svg")
    plt.savefig(out, dpi=300)
    out = os.path.join(config.DIR_REPORT, "top-publishers.png")
    plt.savefig(out, dpi=300)
    plt.close()


def eval_published_year_histogram(df):
    x = df[Review.PUBLISHED_YEAR]

    x_min = int(min(x))
    x_max = int(max(x))
    logger.info(f"Bins: {x_min} - {x_max}")
    bins = x_max - x_min


    plt.hist(x, bins, color="C0")
    plt.title("Publikationsdatum")
    plt.xlabel('Jahr')
    plt.ylabel('Anzahl Reviews')
    plt.tight_layout()

    out = os.path.join(config.DIR_REPORT, "publishing-year-hist.svg")
    plt.savefig(out, dpi=300)
    out = os.path.join(config.DIR_REPORT, "publishing-year-hist.png")
    plt.savefig(out, dpi=300)
    plt.close()


def eval_page_histogram(df):
    x = df[Review.PAGES]

    logger.info(f"Mean Pages: {sum(x) / len(x)}")
    # filter all with page count > 2000
    x = list(filter(lambda x: (x < 2000), x))

    x_min = int(min(x))
    x_max = 2000  # int(max(x))

    bins = int((x_max - x_min) / 50)
    logger.info(f"Bins: {x_min} - {x_max} -> {bins}")

    plt.hist(x, bins, color="C0")
    plt.title("Histogram of Page Number")
    plt.xlabel('Pages')
    plt.ylabel('Number of Books')
    plt.tight_layout()

    out = os.path.join(config.DIR_REPORT, "pages-hist.svg")
    plt.savefig(out, dpi=300)

    out = os.path.join(config.DIR_REPORT, "pages-hist.png")
    plt.savefig(out, dpi=300)
    plt.close()


def eval_page_ranking(df: pd.DataFrame, top_n=20):
    srt = df.sort_values(by=Review.PAGES, ascending=False)

    pages = srt[Review.PAGES][:top_n]
    names = srt[Review.ID][:top_n]

    # names = [name.split(".")[0] for name in names]
    names = [str(name) for name in names]
    fig = plt.figure(figsize=(25, 10))

    plt.barh(names, pages, align='center', color="C0")

    plt.title("Number of Pages per Book")
    plt.xlabel('Pages')
    plt.ylabel('Review ID')
    # plt.tight_layout()

    out = os.path.join(config.DIR_REPORT, "pages-ranking.svg")
    plt.savefig(out, dpi=300)
    out = os.path.join(config.DIR_REPORT, "pages-ranking.png")
    plt.savefig(out, dpi=300)

    plt.close()


def main():
    sb.set()
    path = os.path.join(config.DIR_PROCESSED, "reviews.pkl")

    df = pd.read_pickle(path)
    df = utils.default_df_filter(df)
    logger.info(f"Reviews: {len(df)}")

    #
    df = df[~df[Review.PAGES].isnull()]
    df = df[~df[Review.PUBLISHED_YEAR].isnull()]

    df.set_index(Review.DATE, inplace=True)
    # filter all reviews that do not contain information about the number of pages

    # eval_over_time(df, key="Y")
    eval_publishers_ranking(df)
    eval_published_year_histogram(df)
    eval_page_histogram(df)
    eval_page_ranking(df)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
