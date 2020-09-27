# -*- coding: utf-8 -*-
"""
You will need to install cartopy for this
"""
import logging.config

import cartopy.feature as cfeature
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import seaborn as sb

import pandas as pd
import os

import config

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main():
    sb.set()

    df = pd.read_pickle(os.path.join(config.DIR_PROCESSED, "locations.pkl"))

    extent = [0, 20, 58, 45]  # left angle, right angle, upper angle, lower angle

    fig = plt.figure(figsize=(16, 9))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent(extent)

    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.BORDERS, edgecolor="gray")
    ax.add_feature(cfeature.LAND, edgecolor='black')
    ax.add_feature(cfeature.LAKES, edgecolor='black')
    ax.add_feature(cfeature.RIVERS)
    ax.gridlines()

    for city, row in df.iterrows():
        size = row["review_count"]
        lng = row["lng"]
        lat = row["lat"]
        logger.info(f"{city} -> {size}")

        ax.plot(lng, lat, 'go', markersize=size / 2, transform=ccrs.Geodetic())
        ax.text(lng, lat, city, fontsize=6, horizontalalignment='center')

    path = os.path.join(config.DIR_REPORT, "map.svg")
    logger.info(f"Saving to {path}")
    fig.canvas.draw()
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    # plt.show()


if __name__ == "__main__":
    main()
