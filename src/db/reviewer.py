# -*- coding: utf-8 -*-
"""

"""


class Reviewer(object):
    """

    """
    # reviewer
    NAME = "reviewer_name"
    GENDER = "reviewer_gender"
    TITLES = "reviewer_titles"
    HIGHEST_TITLE = "reviewer_title_highest"
    DESC = "reviewer_description"
    LOCATION = "reviewer_location"
    ID = "reviewer_id"

    KEYWORDS = "keywords"
    KEYWORD_COUNT = "keyword_count"
    KEYWORDS_COUNT = "keyword_counts"
    REVIEW_COUNT = "review_count"

    PAGE_SUM = "page_sum"
    PAGE_MEAN = "page_mean"

    WORD_SUM = "word_sum"
    WORD_MEAN = "word_mean"

    FIRST_REVIEW_DATE = "first_review"
    LATEST_REVIEW_DATE = "latest_review"

    LOCATION = "location"

    def __init__(self):
        self.id = None
        self.name = None
        self.gender = None
        self.titles = None
        self.description = None
        self.location = None
