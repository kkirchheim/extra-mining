# -*- coding: utf-8 -*-
"""

"""
import logging.config
import os

import matplotlib.pyplot as plt
import seaborn as sb

import pandas as pd
import config
from db import Review
import utils

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

n_keywords = 20


def main():
    sb.set()

    path = os.path.join(config.DIR_PROCESSED, "reviews.pkl")
    df = pd.read_pickle(path)
    logger.info("Reviews: %s", len(df))
    utils.default_df_filter(df)

    keywords = {}

    for keys in df[Review.KEYWORDS]:
        # keys = value.replace("\n", ";").split(";")

        for key in keys:
            if key != "":
                if keywords.get(key) is not None:
                    count = keywords.get(key)
                    keywords[key] = count + 1
                else:
                    keywords[key] = 1
                # keywords.append(key)

    # logger.info(keywords)
    logger.info("Keywords: %d", len(keywords.keys()))

    # create ranking list
    keyword_list = []

    for key, count in keywords.items():
        keyword_list.append((key, count))

    keyword_list.sort(key=lambda e: e[1], reverse=True)

    # print top 10 keywords
    logger.info(keyword_list[:n_keywords])

    keys = []
    vals = []

    for key, val in keyword_list:
        keys.append(key)
        vals.append(val)

    # logger.info(vals)

    # draw bar chart with top 10 keywords
    plt.barh(keys[:n_keywords], vals[:n_keywords], align='center', color="C0")
    plt.title("Top Keywords")
    plt.tight_layout()
    out_path = os.path.join(config.DIR_REPORT, "top-keywords.svg")
    plt.savefig(out_path, dpi=300)
    out_path = os.path.join(config.DIR_REPORT, "top-keywords.png")
    plt.savefig(out_path, dpi=300)
    plt.close()

    # plot freq of occurence
    plt.plot(vals)
    plt.title("Keyword Occurrences")
    plt.tight_layout()

    out_path = os.path.join(config.DIR_REPORT, "keyword-occurrences.svg")
    plt.savefig(out_path, dpi=300)
    out_path = os.path.join(config.DIR_REPORT, "keyword-occurrences.png")
    plt.savefig(out_path, dpi=300)
    plt.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
