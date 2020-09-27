# -*- coding: utf-8 -*-
"""
Topic modeling using LDA. Did not quite work.
"""
import logging.config

import os
import pickle

from sklearn.decomposition import LatentDirichletAllocation

import utils
import config

logger = logging.getLogger(__name__)
logging.config.dictConfig(config.LOGGING_CONFIG)


def get_stop_words():
    stop_words = []

    with open(config.PATH_STOP_WORDS, "r") as f:
        for word in f:
            word = word.replace("\n", "")
            word = word.replace("\r", "")

            if word.startswith("#"):
                continue

            stop_words.append(word)

    return stop_words


def print_top_words(model, feature_names, n_top_words):
    for topic_idx, topic in enumerate(model.components_):
        message = "Topic #%d: " % topic_idx
        message += " ".join([feature_names[i]
                             for i in topic.argsort()[:-n_top_words - 1:-1]])
        logger.info(message)


def main(n_components=10):
    """
    Creates the keyword co occurrence matrix and a list of keywords, ordered by count

    """
    matrix_file = os.path.join(config.DIR_INTERIM, "word-matrix.pkl")
    logger.info(f"Loading: {matrix_file}")

    with open(matrix_file, "rb") as f:
        word_matrix = pickle.load(f)

    n_reviews = word_matrix.shape[0]

    feature_names = utils.load_list(os.path.join(config.DIR_INTERIM, "feature-names.txt"))

    lda = LatentDirichletAllocation(n_components=n_components)

    logger.info(f"Calculating LDA with {n_components} components.")
    lda_matrix = lda.fit_transform(word_matrix)

    logger.info(f"Matrix Type: {type(lda_matrix)}")
    logger.info(f"Matrix Shape: {lda_matrix.shape}")
    logger.info(f"Reviews: {n_reviews}")

    matrix_path = os.path.join(config.DIR_INTERIM, "lda-matrix.pkl")
    logger.info(f"Saving LDA matrix to '{matrix_path}'")
    with open(matrix_path, "wb") as f:
        pickle.dump(lda_matrix, f)

    print_top_words(lda, feature_names, 30)
    logger.info("Done")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
