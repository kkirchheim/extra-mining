# -*- coding: utf-8 -*-
"""
This script extracts information from the raw downloaded html files.
All other scripts build on top of the information extracted from this script.
"""
import logging.config
import os
import re
from os.path import isfile, join

import bs4
import numpy as np
import pandas

import config
import utils
from utils import AcademicTitleCategory
from constants import *
from db import Review
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import concurrent.futures

logger = logging.getLogger(__name__)
logging.config.dictConfig(config.LOGGING_CONFIG)


class MyException(Exception):
    pass


reviewer_gender_map = dict()


def get_id_from_file_name(file):
    file = os.path.basename(file)
    str_id = os.path.splitext(file)[0]
    return int(str_id)


def extract_category(current_review: Review, soup):
    """
    Not all articles are assigned to a category. Additionally, some articles are assigned to multiple categories.
    ATM, we are unable to handle this.

    Parameters
    ----------
    current_review
    soup

    Returns
    -------

    """
    links = []
    for link in soup.findAll('a', attrs={'href': re.compile("^https://")}):
        links.append(link.get('href'))

    # find category

    url = config.URL_WEBSITE + "/stellenmarkt/index.php?auswahl="
    for link in links:
        if link.startswith(url):
            category = link.split("=")[1]
            current_review.category = category
            logger.info("Category: %s", category)
            return


def extract_reviewer_id(current_review, contentbox):
    # find reviewer id
    for link in contentbox.findAll('a', attrs={'href': re.compile(r"^/rezensionen/rezensionen\.php")}):
        href = link.get('href')
        reviewer_id = int(href.split("=")[1])
        logger.info("Reviewer-ID: %d", reviewer_id)
        current_review.reviewer_id = reviewer_id
        return

    msg = "Count not find reviewer id"
    raise MyException(msg)


def process_links(current_review: Review, contentbox, ignore=None):
    """
    Processes all links in the contentbox. Finds the DNB link (with the isbn) and the reviewer id

    Parameters
    ----------
    current_review
    contentbox
    ignore

    Returns
    -------

    """
    links = []

    for link in contentbox.findAll('a', attrs={'href': re.compile("^http://")}):
        links.append(link.get('href'))

    for link in contentbox.findAll('a', attrs={'href': re.compile("^https://")}):
        links.append(link.get('href'))

    # find dnb link and isbn
    url = "http://portal.d-nb.de/opac.htm?query="
    for link in links:
        if link.startswith(url):
            logger.debug("DNB-Link: %s", link)
            current_review.dnb_link = link

            isbn = link[len(url):].split("&")[0]
            current_review.isbn = isbn
            break

    # filter ignored links
    filtered_links = []

    for link in links:
        flag = False

        for url in ignore:
            if url in link:
                flag = True
                break

        if not flag:
            logger.debug("Found link '%s'", link)
            filtered_links.append(link)

    current_review.links = filtered_links
    return True


def extract_review_headings(current_review, contentbox):
    """
    Extract headings from text

    :param current_review:
    :param contentbox:
    :return:
    """
    headings = list()

    for heading in contentbox.find_all('h2'):
        head = heading.text

        if head is None or len(head) == 0:
            continue

        head = utils.clean_html_text(head)
        headings.append(head)

    logger.debug(f"Heading: '{headings}'")
    current_review.headings = headings
    return True


def extract_review_text(current_review, contentbox):
    text_fragments = list()

    logger.debug("Extracting text...")

    for s in contentbox.find_all(["p"])[3:-7]:

        # t = " ".join(s.stripped_strings)
        t = s.text

        if t is None or len(t) == 0:
            continue

        t = utils.clean_html_text(t)

        if t.startswith("Besprochenes Werk kaufen") \
                or t.startswith("Rezensent") \
                or t.startswith("Rezensentin") \
                or t.startswith("Rezension von"):
            continue

        text_fragments.append(t)

    text = " ".join(text_fragments)

    if len(text) == 0:
        msg = "Could not extract text ({})".format(current_review.id)
        raise MyException(msg)

    current_review.text = text.strip(" ")
    word_count = len(text.split(" "))
    current_review.word_count = word_count

    logger.debug("Text: '%s'", text.replace('\n', ''))
    logger.debug(f"Words: '{word_count}'")
    return True


def extract_reviewer_title(current_review: Review, reviewer_name):
    """
    Extracts the reviewers title (e.g. Prof. Dr. phil) from the given name

    :param current_review:
    :param reviewer_name:
    :return:
    """

    known_titles = utils.load_list(config.PATH_TITLES)
    nameparts = reviewer_name.split(" ")

    if len(nameparts) == 0:
        current_review.reviewer_title = [AcademicTitleCategory.none]
        logger.info("Reviewer Title: %s", current_review.reviewer_title)
        return True

    titles = []

    for part in nameparts:

        if "Dr." in part or part == "Dr":
            logger.info("Found PhD")
            titles.append(AcademicTitleCategory.phd)

        if "Prof" in part:
            logger.info("Found Prof.")
            titles.append(AcademicTitleCategory.prof)

        if "MSc" in part or part == "M" or "M.Sc." in part:
            logger.info("Found Master")
            titles.append(AcademicTitleCategory.master)

        if part == "BSc":
            logger.info("Found Bachelor")
            titles.append(AcademicTitleCategory.bachelor)

        if part == "Mag.":
            logger.info("Found Magister")
            titles.append(AcademicTitleCategory.magister)

        if "Dipl." in part or "Diplom" in part or "Dipl-" in part:
            logger.info(f"Found: {part} (Diploma)")
            titles.append(AcademicTitleCategory.diploma)

    if len(titles) == 0:
        flag = False
        for part in nameparts:
            if part in known_titles:
                logger.warning(f"Unhandled Title: {part}")
                if not flag:
                    titles.append(AcademicTitleCategory.unknown)
                    flag = True
            else:
                pass

    current_review.reviewer_title = titles
    current_review.reviewer_highest_title = AcademicTitleCategory.get_highest(titles)

    if current_review.reviewer_highest_title is None:
        current_review.reviewer_highest_title = AcademicTitleCategory.none
        # This should be unreachable ...
        # raise MyException("Highest Title is None")

    logger.info(f"Reviewer Title: {current_review.reviewer_title}")
    logger.info(f"Reviewer Highest Title: {current_review.reviewer_highest_title}")
    return True


def extract_reviewer(current_review: Review, soup):
    """
    Look for Name, Gender and Description of reviewer in article

    :param current_review:
    :param soup:

    :return:
    """
    reviewer_name = None
    reviewer_desc = None
    reviewer_gender = None

    iterator = soup.stripped_strings
    for s in iterator:
        if s == "Rezensentin":
            reviewer_name = next(iterator)
            reviewer_desc = next(iterator)
            reviewer_gender = GENDER_FEMALE
            reviewer_gender_map[reviewer_name] = reviewer_gender
            break
        elif s == "Rezensent":
            reviewer_name = next(iterator)
            reviewer_desc = next(iterator)
            reviewer_gender = GENDER_MALE
            reviewer_gender_map[reviewer_name] = reviewer_gender
            break
        elif s == "Rezension von":
            reviewer_name = next(iterator)
            reviewer_desc = next(iterator)
            # actually, we should match using ids. however we assume that an equal name implies an equal gender
            reviewer_gender = reviewer_gender_map.get(reviewer_name, GENDER_ELSE)
            break

    if reviewer_name is None or reviewer_desc is None or reviewer_gender is None:
        msg = f"No Reviewer found ({current_review})"
        raise MyException(msg)

    else:
        reviewer_desc = utils.clean_html_text(reviewer_desc)

        # filter missing descriptions
        ex = re.findall(r'Alle \d+ Rezensionen von', reviewer_desc)
        if len(ex) != 0 or reviewer_desc == "E-Mail" or reviewer_desc == "Homepage":
            reviewer_desc = None

        current_review.reviewer_name = utils.clean_html_text(reviewer_name)
        current_review.reviewer_description = reviewer_desc
        current_review.reviewer_gender = reviewer_gender

    logger.info("Reviewer: '%s' (Gender: %s)", reviewer_name, current_review.reviewer_gender)
    logger.info("Reviewer Description: '%s'", reviewer_desc)
    extract_reviewer_title(current_review, current_review.reviewer_name)

    return True


def extract_dates(current_review: Review, soup):
    for s in soup.stripped_strings:
        if "Rezension vom" in s:
            date = re.findall(r'[0-3][0-9]\.[0-1][0-9]\.[1-2][0-9][0-9][0-9]', s)

            if len(date) == 0:
                msg = "No Date found (%s)" % current_review
                raise MyException(msg)

            # first will be the creation date
            d_publish = date[0]
            dd, mm, yyyy = str(d_publish).split(".")
            date_published = np.datetime64("{}-{}-{}".format(yyyy, mm, dd))
            current_review.date = date_published
            logger.debug("Published Date: '%s'", date_published)

            # second will be the access date
            if len(date) == 2:
                d_access = date[1]
                dd, mm, yyyy = str(d_access).split(".")
                date_access = np.datetime64("{}-{}-{}".format(yyyy, mm, dd))
                current_review.date_access = date_access
                logger.debug("Published Date: '%s'", date_access)

            if len(date) > 2:
                logger.warning("To many dates found: %s", ";".join(date))

    return True


def extract_description(current_review: Review, soup):
    """

   :param current_review:
   :param soup:
   :return:
   """
    meta = soup.find("meta", {"name": "description"})

    if meta is None:
        msg = "Could not find meta tag for %s" % current_review
        raise MyException(msg)

    current_review.description = meta['content']
    logger.debug("Description: %s", current_review.description)
    return True


def extract_meta_keywords(current_review: Review, soup, filter_annotation_keywords=True):
    """

    Parameters
    ----------
    filter_annotation_keywords: filter keywords used to annotate articles by the website (e.g. as recommended)
    current_review
    soup

    Returns
    -------

    """
    meta = soup.find("meta", {"name": "keywords"})

    if meta is None:
        msg = "Could not find meta tag for %s" % current_review
        raise MyException(msg)

    # for some reason, keywords are sometimes seperated by newline
    keywords = meta['content'].replace("\n", ";").split(";")
    keywords = list(set(filter(lambda keyword: keyword != "", keywords)))

    if filter_annotation_keywords:
        keywords = list(set(filter(lambda keyword: not keyword.startswith("_"), keywords)))

    current_review.keywords = keywords
    logger.debug("Keywords: %s", keywords)
    return True


def process_review_header(current_review: Review, header) -> None:
    """

    Parameters
    ----------
    current_review
    header

    Returns
    -------

    """
    logger.debug(f"Header: {header}")

    segments = header.split(".")

    if len(segments) == 0:
        msg = "Broken Header: '%s'", header
        raise MyException(msg)

    title_segments = []

    # matches 3 groups: [publisher] ([location]) [year]
    publisher_re = re.compile(r"(.+)\s+\((.+)\)\s+(\d+)")
    page_re = re.compile(r"(\d+) Seiten")

    for i, segment in enumerate(segments):
        segment = segment.strip()
        publishing_match = publisher_re.match(segment)
        page_match = page_re.match(segment)

        if segment.find("ISBN") != -1:
            isbn = segment.split(" ")
            if len(isbn) < 2:
                logger.warning(f"ISBN extraction Failed for {current_review}")
                continue

            current_review.isbn = isbn[1]
            logger.debug("ISBN: '%s'", current_review.isbn)

        elif segment.find("EUR") != -1 or segment.find("sFr") != -1:
            # TODO: fix
            parts = segment.split(" ")
            price = parts[0]
            price = price.replace(" ", "")
            price = price.replace(",", ".")
            current_review.price = float(price)
            logger.debug(f"Price: {current_review.price}")

            currency = parts[1].strip(". ")
            current_review.price_unit = currency
            logger.debug(f"Price Unit: '{current_review.price_unit}'")

        elif publishing_match is not None:
            # e.g. Votum Verlag (Münster) 2000, or Fachhochschulverlag (Frankfurt am Main) 1999

            publisher = publishing_match.group(1)
            logger.debug(f"Publisher: '{publisher}'")
            current_review.publisher = publisher

            location = publishing_match.group(2)
            logger.debug(f"Location: '{location}'")
            current_review.published_location = location

            year = publishing_match.group(3)
            logger.debug(f"Year: {year}")
            current_review.published_year = int(year)

        elif page_match is not None:
            # e.g. ' 424 Seiten'
            match = page_match.group(1)

            if match is None:
                msg = f"Malformed Page Segment: {segment} from {segments}"
                raise MyException(msg)

            current_review.pages = int(match)
            logger.debug(f"Pages: {current_review.pages}")

        else:
            title_segments.append(segment)

    if len(title_segments) > 0:
        current_review.title = ". ".join(title_segments).strip()
        logger.debug(f"Title: '{current_review.title}'")

    if current_review.pages is None:
        logger.warning(f"No Page Segment found ({current_review})")
    if current_review.published_year is None:
        logger.warning(f"No Publisher Segment found ({current_review})")


def extract_from_article_heading(current_review: Review, soup):
    """

    Parameters
    ----------
    current_review
    soup

    Returns
    -------

    """
    first_paragraph = list(soup.find_all("p"))[0]

    strings = []
    strings.extend(first_paragraph.stripped_strings)

    heading = []
    for s in strings[:3]:
        # sometimes, the strings are not properly stripped
        heading.append(utils.clean_html_text(s))

    heading = " ".join(heading)

    try:
        heading = heading.split(":")[1]
    except IndexError:
        # heading does not contain ':'
        raise MyException(f"Malformed Article Heading: '{heading}'")
    else:
        process_review_header(current_review, heading)


def guess_city(current_review: Review, cities):
    found_cities = []

    if current_review.reviewer_description:
        for city in cities:
            n_city = " " + city + " "
            if n_city in current_review.reviewer_description:
                logger.debug("Found City: %s", city)
                found_cities.append(city)
                continue
            n_city = " " + city + "."
            if n_city in current_review.reviewer_description:
                logger.debug("Found City: %s", city)
                found_cities.append(city)

            n_city = " " + city + ","
            if n_city in current_review.reviewer_description:
                logger.debug("Found City: %s", city)
                found_cities.append(city)

            n_city = " " + city + ";"
            if n_city in current_review.reviewer_description:
                logger.debug("Found City: %s", city)
                found_cities.append(city)

            n_city = " " + city + "/"
            if n_city in current_review.reviewer_description:
                logger.debug("Found City: %s", city)
                found_cities.append(city)

            n_city = "/" + city
            if n_city in current_review.reviewer_description:
                logger.debug("Found City: %s", city)
                found_cities.append(city)

            n_city = " " + city
            if current_review.reviewer_description.endswith(n_city):
                logger.debug("Found City: %s", city)
                found_cities.append(city)

    current_review.reviewer_location = found_cities


def is_not_found(soup) -> bool:
    """
    :param soup:
    :return:
    """
    title = soup.find("title").text.strip()

    if "Seite nicht gefunden" in title:
        return True

    return False


def process_single_file(path, filter_urls, cities) -> Review:
    logger.info(f"Processing file: '{path}'")
    review_id = get_id_from_file_name(path)

    current_review = Review(identifier=review_id)

    with open(path, "r") as f:
        content = f.read()
        soup = bs4.BeautifulSoup(content, features="html.parser")

        # filter 404
        if is_not_found(soup):
            logger.info(f"Review {current_review} not found (404)")
            current_review.not_found = True
        else:
            try:
                extract_meta_keywords(current_review, soup)
                extract_description(current_review, soup)

                contentboxes = soup.find_all("div", attrs={"class": "contentbox"})
                main_content = contentboxes[0]
                extract_from_article_heading(current_review, main_content)

                # from text
                extract_dates(current_review, main_content)
                extract_reviewer(current_review, main_content)
                extract_review_text(current_review, main_content)
                extract_review_headings(current_review, main_content)
                process_links(current_review, main_content, ignore=filter_urls)
                extract_reviewer_id(current_review, main_content)

                # extract category from other contentbox
                extract_category(current_review, contentboxes[2])

                # from reviewer description
                guess_city(current_review, cities=cities)

            except KeyboardInterrupt as e:
                # reraise keboard interrupt
                raise e
            except MyException as e:
                logger.warning(f"{e}")
                current_review.parsed_success = False
            except Exception as e:
                logger.exception(e)
                current_review.parsed_success = False
            else:
                logger.info(f"File Processed: '{path}'")

    return current_review


def main(csv_path=os.path.join(config.DIR_PROCESSED, "reviews.csv"),
         pickle_path=os.path.join(config.DIR_PROCESSED, "reviews.pkl"),
         n_processes=None):
    """

    Parameters
    ----------
    csv_path csv output
    pickle_path pickled dataframe output
    n_processes number of workers to use
    Returns
    -------

    """
    allfiles = [f for f in os.listdir(config.DIR_RAW_HTML) if isfile(join(config.DIR_RAW_HTML, f)) and str(f)[0] != "."]
    allfiles = [os.path.join(config.DIR_RAW_HTML, f) for f in allfiles]

    logger.info(f"Data dir contains {len(allfiles)} files")
    allfiles.sort(key=get_id_from_file_name)

    n_notfound = 0
    n_parse_failed = 0

    df_rows = []

    filter_urls = utils.get_ignore_urls()
    german_cities = utils.get_german_cities()

    with ProcessPoolExecutor(max_workers=n_processes) as pool:

        jobs = {}
        for file in allfiles:
            future = pool.submit(process_single_file, file, filter_urls=filter_urls, cities=german_cities)
            jobs[future] = file

        for future in concurrent.futures.as_completed(jobs):
            res = future.result()
            if res.not_found:
                n_notfound += 1
                continue

            if not res.parsed_success:
                n_parse_failed += 1
                continue

            df_rows.append(res.to_dict())

    logger.info("All files processed.")
    logger.info("Creating dataframe ...")
    df = pandas.DataFrame(df_rows)
    df.set_index(Review.ID, drop=False, inplace=True)
    df.sort_values(by=Review.DATE, inplace=True, ascending=True)

    unfound_ratio = n_notfound / len(allfiles)
    unparsed_ratio = n_parse_failed / (len(allfiles) - n_notfound)

    logger.warning(f"Not found: {n_notfound}/{len(allfiles)} {unfound_ratio:.2%}")
    logger.warning(f"Not parsable: {n_parse_failed}/{len(allfiles) - n_notfound} ({unparsed_ratio:.2%})")
    logger.warning(f"Parsable: {len(allfiles) - n_notfound - n_parse_failed}")

    utils.save_gephi_csv(df, csv_path)

    logger.info(f"Saving to '{pickle_path}'")
    df.to_pickle(pickle_path)
    logger.info("Done")
    return


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
