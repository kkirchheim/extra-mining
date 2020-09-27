# -*- coding: utf-8 -*-
"""
Extracts important keywords from the text of reviews and creates files for gephi
"""
import logging.config
import os
import pickle

import numpy as np
import pandas as pd
from nltk import word_tokenize
from nltk.stem.snowball import GermanStemmer
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from collections import Counter
# required for parsing
# import nltk

import spacy


#
import config
import utils
from db import Review
import constants

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# nltk.download('punkt')

stemming_progress: utils.EtaCounter = None


class StemmingTokenizer(object):
    def __init__(self, filtering="'…›‹‚`´-+_*‛”▪∅€†’#$ ./\\"):
        self.stem = GermanStemmer()
        self.count = 0
        self.filtering = filtering
        self.nlp = spacy.load('de_core_news_sm')

    def __call__(self, doc):
        global stemming_progress
        tokens = self.nlp(doc.lower())  # word_tokenize(doc, language='german')
        new_tokens = []

        for t in tokens:
            t = t.lemma_
            for ch in self.filtering:
                if ch in t:
                    t = t.replace(ch, "")

            # remove leading dash
            if len(t) > 2 and t[0] == "–":
                t = t[1:]

            new_tokens.append(t)

        if stemming_progress:
            stemming_progress.next()
            self.count += 1

            if not self.count % 50:
                logger.info(
                    f"Vectorizing -> {self.count / stemming_progress.get_limit():.2%} ETA: {stemming_progress.get_pretty_eta()}")

        return [self.stem.stem(t) for t in new_tokens]


def process(i_review, tfidf_matrix, feature_names, word_matrix, n_keywords=5):
    """

    Parameters
    ----------
    i_review
    tfidf_matrix
    feature_names
    word_matrix
    n_keywords

    Returns
    -------

    """
    row = tfidf_matrix[i_review].toarray().flatten()
    ranks = row.argsort()[-n_keywords:][::-1]

    keywords = []
    scores = []
    counts = []

    for n, i_rank in enumerate(ranks):
        keyword = feature_names[i_rank]

        score = tfidf_matrix[i_review, i_rank]
        count = word_matrix[i_review, i_rank]

        keywords.append(keyword)
        scores.append(score)
        counts.append(count)

    return keywords, scores, counts


def dump_feature_names(feature_names):
    """

    Parameters
    ----------
    feature_names

    Returns
    -------

    """
    path_feature_names = os.path.join(config.DIR_INTERIM, "feature-names.txt")
    logger.info(f"Writing feature names to '{path_feature_names}'")
    with open(path_feature_names, "w") as f:
        for word in feature_names:
            f.write(word + "\n")


def dump_word_matrix(word_matrix):
    word_matrix_path = os.path.join(config.DIR_INTERIM, "word-matrix.pkl")
    logger.info(f"Saving word matrix to '{word_matrix_path}'")
    with open(word_matrix_path, "wb") as f:
        pickle.dump(word_matrix, f)


def dump_tfidf_matrix(tfidf_matrix):
    tfidf_matrix_path = os.path.join(config.DIR_INTERIM, "tf-idf-matrix.pkl")
    logger.info(f"Saving TF-IDF matrix to '{tfidf_matrix_path}'")
    with open(tfidf_matrix_path, "wb") as f:
        pickle.dump(tfidf_matrix, f)


def vectorize(corpus, stop_words=utils.get_stop_words()):
    tokenizer = StemmingTokenizer()
    cv = CountVectorizer(stop_words=stop_words, tokenizer=tokenizer)
    word_matrix = cv.fit_transform(corpus)
    return word_matrix, cv.get_feature_names()


def get_top_words(word_matrix, feature_names, top=100) -> pd.DataFrame:
    n_words = len(feature_names)

    sums = np.sum(word_matrix, axis=0)

    logger.info(f"Sums: {sums.shape}")

    ranks = np.argsort(sums[0, :])
    logger.info(f"Ranks: {ranks[0, 0]}")

    data = []

    # print top 100 words
    for i in range(n_words - top, n_words):
        index = ranks[0, i]

        name = feature_names[index]
        count = sums[0, index]

        logger.info(f"{name} -> {count}")
        entry = dict()
        entry["word"] = name
        entry["count"] = count
        data.append(entry)

    return pd.DataFrame(data)


def main(min_review_words=100, n_keywords=5, max_keywords=5000):
    """
    Creates the keyword co occurence matrix and a list of keywords, ordered by count
    :return:
    """
    global stemming_progress

    path = os.path.join(config.DIR_PROCESSED, "reviews.pkl")
    logger.info(f"Reading: '{os.path.abspath(path)}'")

    df = pd.read_pickle(path)
    df = utils.default_df_filter(df)
    logger.info(f"Successfully parsed reviews: {len(df)}")

    # filter reviews without text
    df_filtered = df[df[Review.WORD_COUNT] >= min_review_words]
    corpus = [text for text in df_filtered[Review.TEXT]]
    # corpus = corpus[:2000]
    n_reviews = len(corpus)
    logger.info(f"Filtered reviews: {len(df_filtered)}")

    logger.info("Vectorizing ...")
    stemming_progress = utils.EtaCounter(n_reviews)
    stemming_progress.start()
    word_matrix, feature_names = vectorize(corpus)

    n_words = len(feature_names)

    logger.info(f"Unique Words: {n_words}")
    dump_feature_names(feature_names)
    dump_word_matrix(word_matrix)

    get_top_words(word_matrix, feature_names)

    logger.info("Calculating TFIDF-Scores ...")
    # calculate tf idf scores
    tfidf = TfidfTransformer()
    tfidf_matrix = tfidf.fit_transform(word_matrix)
    dump_tfidf_matrix(tfidf_matrix)

    # prepare pandas dataframe
    data = []

    items = [t for t in zip(df_filtered.index.tolist(), range(n_reviews))]

    # construct pandas dataframe
    tfidf_data = []
    for review_id, review_idx in items:
        entry = {}
        entry["id"] = review_id
        entry["tfidf"] = tfidf_matrix[review_idx]
        tfidf_data.append(entry)

    mydf = pd.DataFrame(tfidf_data)
    path = os.path.join(config.DIR_PROCESSED, "tfidf-dataframe.pkl")
    logger.info(f"Saving TF-IDF-dataframe to '{path}'")
    mydf.to_pickle(path)

    keyword_counter = Counter()

    eta = utils.EtaCounter(len(items))
    eta.start()

    for review_id, review_idx in items:
        e = eta.next()
        if eta.get_current() % 50 == 0:
            logger.info(f"ETA: {utils.sec2time(e)} n: {eta.get_current()}/{len(items)}")

        keywords, scores, counts = process(review_idx, tfidf_matrix, feature_names, word_matrix, n_keywords=n_keywords)

        for keyword in keywords:
            keyword_counter[keyword] += 1

        entry = dict()
        entry[Review.ID] = review_id
        entry[Review.KEYWORDS] = keywords
        entry["keywords_scores"] = scores
        entry["keywords_count"] = counts
        data.append(entry)

    logger.info("Processing finished")

    data2 = []
    for key, count in keyword_counter.items():
        entry = dict()
        entry[constants.GEPHI_ID] = key
        entry[constants.GEPHI_LABEL] = key
        entry["Count"] = count
        data2.append(entry)

    df2 = pd.DataFrame(data2)
    df2.sort_values(by="Count", ascending=False, inplace=True)

    # get relevant keywords
    df_copy = df2[df2["Count"] >= 2][:max_keywords]
    keywords = set(df_copy[constants.GEPHI_ID][:max_keywords])

    df2.set_index(constants.GEPHI_ID, inplace=True)

    keywords_path = os.path.join(config.DIR_PROCESSED, "keywords-extracted-nodes.csv")
    logger.info(f"Saving CSV to '{keywords_path}'")
    utils.save_gephi_csv(df2, keywords_path)

    df = pd.DataFrame(data)
    df.set_index(Review.ID, inplace=True)

    keywords_path = os.path.join(config.DIR_PROCESSED, "keywords-extracted.csv")
    utils.save_gephi_csv(df, keywords_path)

    keywords_path = os.path.join(config.DIR_PROCESSED, "keywords-extracted.pkl")
    df.to_pickle(keywords_path)

    cooc_mat = utils.df_create_co_occurence_matrix(df, keywords)
    cooc_path = os.path.join(config.DIR_PROCESSED, "keywords-extracted-cooc.csv")
    utils.save_gephi_csv(cooc_mat, cooc_path)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
