# -*- coding: utf-8 -*-
"""
Evaluates Reviewers
"""
import logging.config
import os

import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import seaborn as sb


import config
from db import Review, Reviewer
import utils
from utils import AcademicTitleCategory
from constants import *

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def get_reviewers_for_group(df):
    grouper = pd.Grouper(key=Review.REVIEWER_ID)
    groups = df.groupby(grouper)

    reviewers = []

    for reviewer_id, group in groups:
        reviewer = dict()
        name = group[Review.REVIEWER_NAME].values[0]
        gender = group[Review.REVIEWER_GENDER].values[0]
        titles = group[Review.REVIEWER_TITLE].values[0]
        count = len(group)

        reviewer[Reviewer.NAME] = name
        reviewer[Reviewer.REVIEW_COUNT] = count
        reviewer[Reviewer.GENDER] = gender

        reviewer[Reviewer.HIGHEST_TITLE] = AcademicTitleCategory.get_highest(titles)

        reviewers.append(reviewer)
        logger.debug(f"{name} ({reviewer_id}) -> {count}")

    return reviewers


def normalize_title(title):
    if title in [AcademicTitleCategory.unknown, AcademicTitleCategory.none, AcademicTitleCategory.bachelor]:
        return AcademicTitleCategory.unknown

    if title in [AcademicTitleCategory.master, AcademicTitleCategory.magister, AcademicTitleCategory.diploma]:
        return AcademicTitleCategory.master

    else:
        return title


def eval_reviewer_title_gender_over_time(df, freq="1Y"):
    """

    Evaluates gender and title over time
    Parameters
    ----------
    df
    freq

    Returns
    -------

    """
    grouper = pd.Grouper(freq=freq)
    groups = df.groupby(grouper)

    entries = []
    entries_gender_barplot = []  # data for the gender barplot
    entries_title_barplot = []  # data for the title barplot

    # labels
    GENDER = "Bezeichnung"
    TITLE = "Titel"
    COUNT = "Personen"
    DATE = "Jahr"

    my_title_cat = [AcademicTitleCategory.prof, AcademicTitleCategory.phd, AcademicTitleCategory.master,
                    AcademicTitleCategory.unknown]

    for date, date_group in groups:
        gender_counter = Counter()
        title_counter = Counter()

        entry = {"date": date}

        reviewers = get_reviewers_for_group(date_group)
        entry["reviewers"] = len(reviewers)
        logger.info(f"Reviewers {date} -> {len(reviewers)}")

        for reviewer in reviewers:
            gender_counter[reviewer[Reviewer.GENDER]] += 1
            title = normalize_title(reviewer[Reviewer.HIGHEST_TITLE])
            title_counter[title] += 1

        for gender in ALL_GENDERS:
            entry[gender] = gender_counter[gender]
            entry[f"{gender}-ratio"] = gender_counter[gender] / sum(gender_counter.values())

            # barplot stufff
            entry_gender_barplot = {DATE: date, COUNT: gender_counter[gender], GENDER: gender}
            entries_gender_barplot.append(entry_gender_barplot)

        for title in my_title_cat:
            entry[f"{title}-ratio"] = title_counter[title] / sum(title_counter.values())
            entry[title] = title_counter[title]

            # barplot stuff
            entry_title_barplot = {DATE: date, COUNT: title_counter[title], TITLE: title}
            entries_title_barplot.append(entry_title_barplot)

        entries.append(entry)

    entries = pd.DataFrame(entries)
    entries_gender_barplot = pd.DataFrame(entries_gender_barplot)
    entries_gender_barplot[DATE] = entries_gender_barplot[DATE].apply(lambda x: str(x.year))

    entries_title_barplot = pd.DataFrame(entries_title_barplot)
    entries_title_barplot[DATE] = entries_title_barplot[DATE].apply(lambda x: str(x.year))

    # gender over time bar-plot
    sb.set(style="whitegrid")
    g = sb.barplot(x=DATE, y=COUNT, hue=GENDER, data=entries_gender_barplot)
    # g.set_xticklabels(rotation=30)
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-genders-ot-bar.pgf"), dpi=300)
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-genders-ot-bar.png"), dpi=300)
    plt.close()

    # title over time barplot
    sb.set(style="whitegrid")
    g = sb.barplot(x=DATE, y=COUNT, hue=TITLE, data=entries_title_barplot)
    # g.set_xticklabels(rotation=30)
    plt.xticks(rotation=45)
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-title-ot-bar.pgf"), dpi=300)
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-title-ot-bar.png"), dpi=300)
    plt.close()

    # gender over time stackplot
    sb.set()
    xs = entries["date"]
    ys = [entries[f"{gender}-ratio"] for gender in ALL_GENDERS]
    labels = [str(gender) for gender in ALL_GENDERS]
    plt.stackplot(xs, ys, labels=labels)
    plt.legend(loc="lower left")
    plt.title(f"Reviewer Gender Ratio ({freq})")
    plt.tight_layout()
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-gender-ot.pgf"))
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-gender-ot.png"))
    plt.close()

    # title over time stackplot
    sb.set(style="white")
    xs = entries["date"]
    ys = [entries[f"{title}-ratio"] for title in my_title_cat]
    labels = [str(title) for title in my_title_cat]
    plt.stackplot(xs, ys, labels=labels)
    plt.legend()
    plt.title(f"Reviewer Title")
    plt.tight_layout()
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-title-ot.pgf"))
    plt.savefig(os.path.join(config.DIR_REPORT, "reviewer-title-ot.png"))
    plt.close()
    sb.set()


def _file_filter(file):
    if "reviewers" not in file:
        return False
    if ".pkl" not in file:
        return False
    return True


def _get_date(file):
    file = os.path.basename(file)
    if file == "reviewers-nodelist.pkl":
        return None

    s = file[len("reviewers-"):-len("-nodelist.pkl")]
    logger.info(f"{file} -> {s}")
    return s


def eval_top_n(df, output_path, n_reviewers=10):
    """
    draw bar chart with top n authors

    Parameters
    ----------
    df
    n_reviewers

    Returns
    -------

    """
    df = df.sort_values(by=Reviewer.REVIEW_COUNT, ascending=False)
    # logger.info(df)

    top_n_names = df[Reviewer.NAME][:n_reviewers]
    top_n_counts = df[Reviewer.REVIEW_COUNT][:n_reviewers]
    top_n_gender = df[Reviewer.GENDER][:n_reviewers]

    col = top_n_gender.apply(lambda x: utils.color_mapping_gender[x])

    # logger.info(top_n_names.values)
    # logger.info(top_n_counts.values)

    plt.barh(top_n_names, top_n_counts, align='center', color=col)
    plt.title("Reviewers")
    plt.tight_layout()

    logger.info(f"Saving to {output_path}")
    plt.savefig(output_path, dpi=300)
    plt.close()


def gender_bar_plot(df, output_path):
    counter = {}

    for gender in utils.GenderCategory:
        counter[gender] = len(df[df[Reviewer.GENDER] == gender])

    keys = [str(key) for key in counter]
    values = [value for value in counter.values()]
    colors = [utils.color_mapping_gender[x] for x in counter]
    plt.bar(keys, values, align='center', color=colors)
    plt.title("Reviewer Gender")
    plt.tight_layout()
    logger.info(f"Saving to '{output_path}'")
    plt.savefig(output_path, dpi=300)
    plt.close()
    return counter


def get_nodelist_files(directory):
    ls = os.listdir(directory)
    files = [os.path.join(config.DIR_PROCESSED, file) for file in ls if _file_filter(file)]
    return files


def main(n_reviewers=20):
    sb.set()

    files = get_nodelist_files(config.DIR_PROCESSED)
    for path in files:
        logger.info(f"Loading {path}")
        df = pd.read_pickle(path)

        if _get_date(path) is None:
            p = os.path.join(config.DIR_REPORT, f"top-reviewers.pgf")
            p2 = os.path.join(config.DIR_REPORT, f"reviewer-genders.pgf")
        else:
            name = f"top-reviewers-{_get_date(path)}.pgf"
            p = os.path.join(config.DIR_REPORT, name)
            name = f"reviewer-genders-{_get_date(path)}.pgf"
            p2 = os.path.join(config.DIR_REPORT, name)

        eval_top_n(df, output_path=p, n_reviewers=n_reviewers)
        eval_top_n(df, output_path=p.replace(".pgf", ".png"), n_reviewers=n_reviewers)

        gender_bar_plot(df, output_path=p2)
        gender_bar_plot(df, output_path=p2.replace(".pgf", ".png"))

    # the following will be based on the reviews
    df = pd.read_pickle(os.path.join(config.DIR_PROCESSED, "reviews.pkl"))
    df = utils.default_df_filter(df)
    logger.info(df.columns.values)
    df.set_index("date", inplace=True)
    logger.info(f"Reviews: {len(df)}")
    logger.info(f"Reviewers: {len(df[Review.REVIEWER_ID].unique())}")

    eval_reviewer_title_gender_over_time(df)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
