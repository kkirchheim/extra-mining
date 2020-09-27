# -*- coding: utf-8 -*-
"""

"""
import logging.config
import os
import seaborn as sb
import numpy as np

import matplotlib.pyplot as plt
import pandas as pd

import config
from db import Review
import utils

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main(path=os.path.join(config.DIR_PROCESSED, "reviews.pkl"), timeslice="Y"):
    sb.set()

    df = pd.read_pickle(path)
    utils.default_df_filter(df)
    df.set_index(Review.DATE, inplace=True)

    logger.info("Empty: %d", len(df[df[Review.WORD_COUNT].isnull()]))
    df = df[~df[Review.WORD_COUNT].isnull()]

    m = np.mean(df[Review.WORD_COUNT])
    logger.info(f"Mean: {m}")
    grouper = pd.Grouper(freq=timeslice)
    groups = df.groupby(grouper)

    dates = []
    count_mean = []

    for date, group in groups:
        dates.append(date)
        count_mean.append(group[Review.WORD_COUNT].mean())
        logger.info(group[Review.WORD_COUNT].mean())

    logger.info(dates)
    logger.info(count_mean)

    # plt.plot(dates, pages_mean)
    # plt.ylim(0,500)
    plt.plot(dates, count_mean)
    plt.title(f"Average review length per {timeslice}")
    plt.tight_layout()
    out_path = os.path.join(config.DIR_REPORT, "review-length.svg")
    plt.savefig(out_path, dpi=300)
    out_path = os.path.join(config.DIR_REPORT, "review-length.png")
    plt.savefig(out_path, dpi=300)
    plt.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
