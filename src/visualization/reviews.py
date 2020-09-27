# -*- coding: utf-8 -*-
"""
Evaluates Reviews
"""
import logging.config
import os

import pandas as pd
import seaborn as sb
import matplotlib.pyplot as plt

import config
from db import Review
import utils
from constants import *

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def eval_reviews_gender_over_time(df, out, time_slice="5Y"):
    grouper = pd.Grouper(freq=time_slice)
    groups = df[Review.REVIEWER_GENDER].groupby(grouper)

    dates = []
    reviewer_gender_count = {gender: [] for gender in ALL_GENDERS}

    for date, group in groups:
        dates.append(date)
        counts = group.value_counts()

        c = {}
        for gender in ALL_GENDERS:
            n = counts.get(gender, 0)
            c[gender] = n
            ratio = n / len(group)

            logger.info(f"{date}: {gender} -> {ratio}")
            reviewer_gender_count[gender].append(ratio)

        keys = [str(key) for key in c]
        values = [value for value in c.values()]
        colors = [utils.color_mapping_gender[x] for x in c]
        plt.bar(keys, values, align='center', color=colors)
        plt.title("Bezeichnung")
        plt.tight_layout()
        output_path = os.path.join(out, f"review-genders-{date}.svg")
        logger.info(f"Saving to '{output_path}'")
        plt.savefig(output_path, dpi=300)

        output_path = os.path.join(out, f"review-genders-{date}.png")
        logger.info(f"Saving to '{output_path}'")
        plt.savefig(output_path, dpi=300)

        plt.close()

        logger.info(80 * "-")

    v = [values for values in reviewer_gender_count.values()]

    logger.info(v)
    # colors = [utils.color_mapping_gender[g] for g in GenderCategory]
    plt.stackplot(dates, *v, labels=ALL_GENDERS)
    plt.legend()
    plt.title("Gender-Ratio per Review")
    plt.tight_layout()

    out_path = os.path.join(out, "review-genders-ot.svg")
    logger.info(f"Saving to {out_path}")
    plt.savefig(out_path, dpi=300)
    out_path = os.path.join(out, "review-genders-ot.png")
    logger.info(f"Saving to {out_path}")
    plt.savefig(out_path, dpi=300)

    plt.close()


def eval_reviews_count_over_time(df, timeslice="Y"):
    """
    Plots the number of reviews over time, grouped by timeslice
    Parameters
    ----------
    df
    timeslice

    Returns
    -------

    """
    df = df.copy()
    df.set_index(Review.DATE, inplace=True)

    grouper = pd.Grouper(freq=timeslice)
    groups = df.groupby(grouper)

    dates = []
    values = []

    for date, group in groups:
        dates.append(date)
        values.append(len(group))
        logger.info(len(group))

    logger.info(dates)
    logger.info(values)

    plt.plot(dates[:-1], values[:-1])
    plt.title(f"Average reviews per {timeslice}")
    plt.tight_layout()

    out_path = os.path.join(config.DIR_REPORT, "uploads-over-time.svg")
    plt.savefig(out_path, dpi=300)

    out_path = os.path.join(config.DIR_REPORT, "uploads-over-time.png")
    plt.savefig(out_path, dpi=300)
    plt.close()


def gender_bar_plot(df, out):
    counter = {}

    for gender in utils.GenderCategory:
        counter[gender] = len(df[df[Review.REVIEWER_GENDER] == gender])

    keys = [str(key) for key in counter]
    values = [value for value in counter.values()]
    colors = [utils.color_mapping_gender[x] for x in counter]
    plt.bar(keys, values, align='center', color=colors)
    plt.title("Reviewer")
    plt.tight_layout()

    path = os.path.join(out, "reviews-gender-bar-plot.svg")
    logger.info(f"Saving to '{path}'")
    plt.savefig(path, dpi=300)

    path = os.path.join(out, "reviews-gender-bar-plot.png")
    logger.info(f"Saving to '{path}'")
    plt.savefig(path, dpi=300)

    plt.close()


def main():
    sb.set()
    path = os.path.join(config.DIR_PROCESSED, "reviews.pkl")
    df = pd.read_pickle(path)
    df = utils.default_df_filter(df)

    logger.info(df.columns.values)
    df.set_index("date", inplace=True)
    logger.info(f"Reviews: {len(df)}")
    logger.info(f"Reviewers: {len(df[Review.REVIEWER_ID].unique())}")

    eval_reviews_gender_over_time(df, config.DIR_REPORT)
    gender_bar_plot(df, config.DIR_REPORT)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
