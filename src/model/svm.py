# -*- coding: utf-8 -*-
"""
Construct a linear SVM to generate article recommendations.
"""
import pickle
import pandas as pd
import os
import config
import logging.config
from sklearn import svm
import numpy as np
import scipy
import time
from db import Review

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main():
    df_tfidf = pd.read_pickle(os.path.join(config.DIR_PROCESSED, "tfidf-dataframe.pkl"))
    df_reviews = pd.read_pickle(os.path.join(config.DIR_PROCESSED, "reviews.pkl"))

    liked = range(100)  # fake liked articles

    # prepare labels
    y = np.zeros(len(df_tfidf))
    for idx, ident in enumerate(df_tfidf["id"]):
        if ident in liked:
            y[idx] = 1

    # use cached matrix, or create new
    tmp_path = os.path.join(config.DIR_INTERIM, "tmp.pkl")
    if os.path.exists(tmp_path):
        with open(tmp_path, "rb") as f:
            tmp = pickle.load(f)
        X = tmp["X"]
        # y = tmp["y"]
    else:
        cols = int(df_tfidf["tfidf"].values[0].shape[1])
        rows = int(len(df_tfidf))

        logger.info(f"{rows} {cols}")
        X = scipy.sparse.csr_matrix((rows, cols), dtype=np.float32)
        y = np.zeros(len(df_tfidf))

        for idx, ident in enumerate(df_tfidf["id"]):
            if ident in liked:
                y[idx] = 1

            X[idx] = df_tfidf["tfidf"].values[idx]

            if idx % 50:
                logger.info(f"{idx / rows:.1%}")

        logger.info(X.shape)
        logger.info(np.unique(y, return_counts=True))

        d = {"X": X, "y": y}
        with open(tmp_path, "wb") as f:
            pickle.dump(d, f)

    # train
    clf = svm.LinearSVC(max_iter=1000, random_state=0, verbose=100, tol=1e-6)

    logger.info("Fitting ...")
    t_start = time.time()
    clf.fit(X, y)
    t_end = time.time()
    logger.info(f"Fitting Finished {t_end - t_start}")

    svm_path = os.path.join(config.DIR_DATA, "svm.pkl")
    with open(svm_path, "wb") as f:
        pickle.dump(clf, f)

    prediction = clf.decision_function(X)

    sortix = np.argsort(-prediction)

    for n, idx in enumerate(sortix[:min(100, len(sortix))]):
        ident = df_tfidf["id"].values[idx]

        if ident in liked:
            continue

        pred = prediction[idx]
        logger.info(f"{n}: {pred} -> {ident}: '{df_reviews.at[ident, Review.TITLE]}'")


if __name__ == '__main__':
    main()
