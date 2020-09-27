# -*- coding: utf-8 -*-
"""
Description of a review.

We initially intended to feed the scraped data into a sql database, that's why this file contains legacy
code for sqlalchemy bindings.
"""


class Review(object):
    """
    Class representing a review
    """

    # review
    ID = "id"
    NOT_FOUND = "not_found"
    DATE_ACCESS = "date_access"
    PARSED_SUCCESS = "parsed_success"
    TITLE = "title"
    CATEGORY = "category"
    DATE = "date"
    TEXT = "text"
    HEADINGS = "headings"
    WORD_COUNT = "word_count"
    LINKS = "links"
    DNB_LINK = "dnb_link"

    # reviewer
    REVIEWER_NAME = "reviewer_name"
    REVIEWER_GENDER = "reviewer_gender"
    REVIEWER_TITLE = "reviewer_title"
    REVIEWER_HIGHEST_TITLE = "reviewer_highest_title"
    REVIEWER_DESC = "reviewer_description"
    REVIEWER_LOCATION = "reviewer_location"
    REVIEWER_ID = "reviewer_id"

    # author
    AUTHORS_NAME = "authors_name"
    AUTHORS_PROFESSION = "authors_profession"
    AUTHORS_COUNTRY = "authors_country"
    AUTHORS_AFFILIATIONS = "authors_affiliations"
    AUTHORS_TITLE = "authors_title"
    AUTHORS_ID = "authors_id"

    # book
    PRICE = "price"
    PRICE_UNIT = "price_unit"
    PAGES = "pages"
    ISBN = "isbn"
    PUBLISHER = "publisher"
    PUBLISHED_YEAR = "published_year"
    PUBLISHED_LOCATION = "published_location"
    KEYWORDS = "keywords"
    DESC = "description"
    DNB_ID = "dnb_id"

    def __init__(self, identifier):
        self.id = identifier

        # meta
        self.not_found = False
        self.date_access = None
        self.parsed_success = True

        # data
        # self.title_short = None
        self.title = None
        self.category = None

        self.reviewer_name = None
        self.reviewer_gender = None
        self.reviewer_title = None
        self.reviewer_highest_title = None
        self.reviewer_description = None
        self.reviewer_location = None
        self.reviewer_id = None

        self.date = None
        self.keywords = None
        self.headings = None
        self.description = None
        self.text = None
        self.word_count = None

        # dnb
        self.authors_name = None
        self.authors_profession = None
        self.authors_country = None
        self.authors_location = None
        self.authors_affiliations = None
        self.authors_id = None
        self.dnb_id = None

        # only for books
        self.price = None
        self.price_unit = None
        self.pages = None
        self.isbn = None
        self.publisher = None
        self.published_year = None
        self.published_location = None

    def __str__(self):
        return "Review: %d" % self.id

    def to_dict(self):
        return {c: getattr(self, c) for c in dir(self) if not (c.startswith("_") or c == "to_dict" or c[0].isupper())}
