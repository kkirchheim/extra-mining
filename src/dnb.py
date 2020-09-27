# -*- coding: utf-8 -*-
"""

"""
import os
import json
import requests
from pymarc import parse_xml_to_array, Record
from io import StringIO
import logging.config
import urllib.parse
import hashlib
from typing import List

import config

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class AuthorityEntry:
    def __init__(self, record: Record):
        self.record = record

    def dump(self):
        logger.info("ID: %s", self.identifier())
        logger.info("Name: %s", self.name())
        logger.info("Acad. Title: %s", self.title())
        logger.info("Profession: %s", self.profession())
        logger.info("Country: %s", self.country_code())
        logger.info("Affiliations: %s", self.affiliations())
        logger.info("Birth Place: %s", self.birth_place())
        logger.info("Birth Year: %s", self.birth_year())

    def name(self) -> str:
        r = self.record["100"]
        if not r:
            return None
        return r["a"]

    def identifier(self) -> str:
        return self.record["024"]["a"]

    def country_code(self) -> str:
        """
        e.g. XA-DE, XA-CH, XA-AT

        Returns
        -------

        """
        country_field = self.record["043"]
        if country_field:
            return country_field["c"]
        else:
            return None

    def title(self) -> str:
        for field in self.record.get_fields("550"):
            field_type = field["4"]
            if field_type == "akad":
                return field["a"]

    def profession(self) -> str:
        for field in self.record.get_fields("550"):
            field_type = field["4"]
            if field_type == "berc":
                return field["a"]

    def affiliations(self) -> list:
        affiliations = []
        for field in self.record.get_fields("551"):
            field_type = field["4"]
            if field_type == "affi":
                affiliations.append(field["a"])

        return affiliations

    def birth_place(self) -> str:
        for field in self.record.get_fields("551"):
            field_type = field["4"]
            if field_type == "ortg":
                return field["a"]

    def birth_year(self) -> str:
        for field in self.record.get_fields("548"):
            field_type = field["4"]
            if field_type == "datl":
                return field["a"]


class BibliographyEntry:
    def __init__(self, record: Record):
        self.record = record

    def dump(self):
        logger.info("ID: %s", self.identifier())
        logger.info("Title: %s", self.title())
        logger.info("Publisher: %s", self.publisher())
        logger.info("Publisher Locations: %s", self.publisher_locations())
        logger.info("Year: %s", self.publishing_year())
        logger.info("Authors: %s", self.authors())
        logger.info("Editors: %s", self.editors())
        logger.info("Contributor: %s", self.contributors())
        logger.info("Keywords: %s", self.keywords())

    def identifier(self) -> str:
        return self.record["016"]["a"]

    def title(self):
        """
        Merges title and subtitle

        Returns
        -------

        """
        try:
            title = self.record['245']['a']
        except TypeError:
            title = None
        if title:
            try:
                title += ". " + self.record['245']['b']
            except TypeError:
                pass

        return title + "."

    def authors(self) -> list:
        authors = list()
        for field in self.record.get_fields("100"):
            if field["0"] is None:
                logger.warning("Missing Author")
                continue

            author_id = field["0"][8:]
            authors.append(author_id)
        return authors

    def contributors(self) -> list:
        contribs = list()
        for field in self.record.get_fields("700"):
            field_type = field["4"]
            if field_type == "ctb":
                if field["0"] is None:
                    logger.warning("Missing Contributor")
                    continue

                contribuor_id = field["0"][8:]  # "mitwirkender"
                contribs.append(contribuor_id)

        return contribs

    def editors(self) -> list:
        editors = list()
        for field in self.record.get_fields("700"):
            field_type = field["4"]
            if field_type == "edt":
                if field["0"] is None:
                    logger.warning("Missing Editor")
                    continue

                editor_id = field["0"][8:]  # "herausgeber"
                editors.append(editor_id)

        return editors

    def keywords(self) -> set:
        keywords = set()
        for field in self.record.get_fields("689"):
            field_type = field["D"]
            if field_type == "s":
                keywords.add(field["a"])
        return keywords

    def publisher(self) -> str:
        return self.record.publisher()

    def publishing_year(self) -> str:
        y = self.record.pubyear()
        if not y:
            return None

        return self.record.pubyear().strip("[]()")

    def publisher_locations(self) -> list:
        locations = []
        entry = self.record["264"]
        if entry:
            for field in entry.get_subfields("a"):
                locations.append(field)

        return locations


def hash_str(s) -> str:
    md = hashlib.md5()
    # TODO: should we use bytes here?
    md.update(s.encode("utf-8"))
    return md.hexdigest()


class DNBConnector:
    def __init__(self,
                 access_token,
                 dnb_url="https://services.dnb.de/sru/dnb",
                 authorities_url="https://services.dnb.de/sru/authorities",
                 version="1.1",
                 cache=True):

        self.access_token = access_token
        self.dnb_url = dnb_url
        self.authorities_url = authorities_url
        self.version = version
        self.use_cache = cache
        self.cache_dir = config.DIR_RAW_DNB

    def _exec_query(self, entry_url, query):
        params = {
            "version": self.version,
            "operation": "searchRetrieve",
            "query": query,
            "recordSchema": "MARC21-xml",
            "accessToken": self.access_token}

        encoded_params = urllib.parse.urlencode(params)
        url = entry_url + "?" + encoded_params

        cache_path = os.path.join(self.cache_dir, "%s.xml" % hash_str(url))

        # if cache is used and file exists, load from cache
        if self.use_cache and os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                xml = f.read()
        else:
            # query DNB
            response = requests.get(url)
            content = response.content
            xml = content.decode("utf-8")

            if self.use_cache:
                # cache to file
                with open(cache_path, "w") as f:
                    f.write(xml)

        f = StringIO(xml)
        records = parse_xml_to_array(f)
        return records

    def _exec_query_auth(self, query):
        return self._exec_query(self.authorities_url, query)

    def _exec_query_bib(self, query):
        return self._exec_query(self.dnb_url, query)

    def query_authority(self, term) -> List[AuthorityEntry]:
        query = f"WOE={term}"

        records = self._exec_query_auth(query)

        if records is None:
            return None

        return [AuthorityEntry(record) for record in records if record is not None]

    def query_bibliography(self, term) -> List[BibliographyEntry]:
        query = f"WOE={term}"
        records = self._exec_query_bib(query)

        if len(records) > 2:
            logger.warning("Found more than 1 record")

        if records is None:
            return None

        return [BibliographyEntry(record) for record in records if record is not None]