# -*- coding: utf-8 -*-
"""
Gather information on different cities, i.e. which city spawns the most reviews.
"""
import logging.config
import os
import pandas as pd
import numpy as np


import config
from db import Reviewer, City
import utils
from constants import *

logging.config.dictConfig(config.LOGGING_CONFIG)

logger = logging.getLogger(__name__)

# coordinates are from a third party website and they might not have an appropriate license
df_coords = pd.read_csv(os.path.join(config.DIR_EXTERNAL, "de.csv"), index_col=0)


def normalize_city_name(name):
    name = name.replace("ö", "o")
    name = name.replace("ü", "u")
    name = name.replace("ß", "ss")
    name = name.replace("ä", "a")
    return name


def get_city_by_name(name):
    """
    TODO: there are bugs
    Parameters
    ----------
    city name of the city

    Returns coordinates of the city as tuple
    -------

    """
    n_name = normalize_city_name(name)

    results = []

    try:
        lat = df_coords.at[n_name, City.LAT]
        lng = df_coords.at[n_name, City.LNG]

        if type(lat) is not np.float64:
            for lo, la in zip(lng, lat):
                city = City(name, lng=lo, lat=la)
                results.append(city)
        else:
            city = City(name, lng=lng, lat=lat)
            results.append(city)

    except KeyError:
        if name != "unknown":
            logger.warning(f"City not found: '{name}'")

    return results


def main():
    path = os.path.join(config.DIR_PROCESSED, "reviewers-nodelist.pkl")
    df = pd.read_pickle(path)
    # df = utils.default_df_filter(df)
    logger.info(df.columns)

    grouper = pd.Grouper(key=Reviewer.LOCATION)
    groups = df.groupby(grouper)

    data = []

    for location, group in groups:
        count = group[Reviewer.LOCATION].count()
        cities = get_city_by_name(location)
        logger.info(f"{location} -> {count} Reviews")

        if cities:
            city = cities[0]

            lat = city.lat
            lng = city.lng

            logger.info(f"Lati: {lat} Long: {lng}")

            subgrouper = pd.Grouper(key=Reviewer.GENDER)
            subgroups = group.groupby(subgrouper)

            male_count = 0.000001
            female_count = 0.000001

            for gender, subgroup in subgroups:
                gender_cont = subgroup[Reviewer.GENDER].count()
                logger.info(f"{gender} -> {gender_cont}")
                if gender == GENDER_MALE:
                    male_count = gender_cont
                elif gender == GENDER_FEMALE:
                    female_count = gender_cont

            entry = dict()

            entry[Reviewer.LOCATION] = location
            entry[GEPHI_ID] = location
            entry[GEPHI_LABEL] = location
            entry[City.LAT] = lat
            entry[City.LNG] = lng
            entry["review_count"] = count
            entry["female_ratio"] = (female_count / (male_count + female_count))

            data.append(entry)

    df2 = pd.DataFrame(data)
    df2.set_index(keys=Reviewer.LOCATION, inplace=True)
    df2.sort_values(by="review_count", inplace=True, ascending=False)
    logger.info(df2)

    out = os.path.join(config.DIR_PROCESSED, "locations.pkl")
    logger.info(f"Saving to {out}")
    df2.to_pickle(out)

    out = os.path.join(config.DIR_PROCESSED, "locations.csv")
    logger.info(f"Saving to {out}")
    utils.save_gephi_csv(df2, out)


if __name__ == '__main__':
    main()
