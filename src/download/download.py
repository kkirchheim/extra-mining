# -*- coding: utf-8 -*-
"""
We added tor support and random user agents for downloading as well as socks proxy support for tor.
"""
import logging.config
import os
import re
import time

import bs4
import click
import requests
import numpy as np

import json

try:
    from stem import Signal, SocketClosed
    from stem.control import Controller
    TOR_AVAILABLE=True
except:
    TOR_AVAILABLE=False

import config
import utils
from utils import EtaCounter

logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def is_not_found(soup) -> bool:
    """

    Parameters
    ----------
    soup

    Returns
    -------

    """
    title = soup.find("title").text.strip()

    if "Seite nicht gefunden" in title:
        return True

    return False


def get_tor_session():
    """
    Tor uses the 9050 port as the default socks port on linux
    """
    session = requests.session()
    session.proxies = {'http': 'socks5://127.0.0.1:9050',
                       'https': 'socks5://127.0.0.1:9050'}
    return session


def get_user_agent():
    path = os.path.join(config.DIR_DATA, "user_agents.txt")
    if not os.path.exists(path):
        return None
    else:
        agents = utils.load_list(path)
        index = np.random.randint(0, len(agents))
        return agents[index]


def scrape(base_url, identifier, session):
    """

    Parameters
    ----------
    base_url
    identifier
    session

    Returns
    -------

    """
    url = f"{base_url}/{identifier}.php"

    logger.info(f"Scraping '{url}'")
    session.headers.update({'User-Agent': get_user_agent()})
    try:
        page = session.get(url)
    except Exception as e:
        logger.exception(e)

    return page.text


def save(path, content):
    logger.info(f"Saving to {path}")
    f = open(path, "w")
    f.write(str(content))
    f.close()


def get_newest_article_id(base_url, session):
    """
    Finding the newest article can be somewhat tricky, as they are not necessarily displayed in
    the order of their publication. We will take the review with the highest id that appears on the
    front page

    :return: id of the newest article
    """

    logger.info(f"Scraping {base_url}")
    page = session.get(base_url)

    soup = bs4.BeautifulSoup(page.text, 'html.parser')

    ids = set()

    session.headers.update({'User-Agent': get_user_agent()})

    for link in soup.findAll('a', attrs={'href': re.compile(r"^rezensionen/\d+")}):
        ln = link.get('href')
        ln = ln.replace("rezensionen/", "")
        ln = ln.replace(".php", "")
        ids.add(int(ln))

    if not ids:
        return 100000

    return max(ids)


def load_tor_controll_token():
    with open(os.path.join(config.DIR_DATA, "secrets.txt")) as f:
        secrets = json.load(f)
        dnb_token = secrets["tor-access-token"]
    return dnb_token


def scrape_loop(r, output, existing_files, sleep, controller=None, update=True):
    eta = EtaCounter(len(r))
    eta.start()

    for i in r:
        eta.next()
        logger.info(f"Fetching Article with id {i}")

        try:
            filename = f"{i}.html"
            path = os.path.join(output, filename)

            if filename in existing_files:
                logger.info("File Exists: '%s'", str(path))

                if not update:
                    continue

            if controller:
                try:
                    controller.signal(Signal.NEWNYM)
                    logger.info("New socks proxy connection")
                    session = get_tor_session()
                except SocketClosed:
                    logger.critical("Socket was closed.")
                    # TODO: establish new connection
                    return
            else:
                session = requests.Session()
            content = scrape(config.URL_REVIEWS, i, session=session)
            save(path, content)

            # sleep some time
            logger.info(f"ETA: {eta.get_pretty_eta()}")
            # time.sleep(sleep)
            time.sleep(sleep + np.random.rand() * sleep)
        except Exception as e:
            logger.exception(e)


@click.command()
@click.option("--limit", "-ul", "upper_limit", type=int, default=27000)
@click.option("--update/--no-update", default=True)
@click.option("--sleep", "-s", "sleep", type=float, default=0.5)
@click.option("--output", "-o", "output", type=click.Path(), default=config.DIR_RAW_HTML)
@click.option("--lower-limit", "-ll", "lower_limit", type=int, default=26413)
@click.option("--tor/--no-tor", default=False)
@click.option("--random/--no-random", default=True)
def main(upper_limit, update, sleep, output, lower_limit, tor, random):
    logger.info(f"Sleep: {sleep}")

    if tor and not TOR_AVAILABLE:
        logger.warning("Tor not available. Install the stem package.")
        tor = False

    existing_files = os.listdir(output)

    if upper_limit is None:
        if tor:
            # we need the controller to change the ip after each request
            with Controller.from_port(port=9051) as controller:
                controller.authenticate(password=load_tor_controll_token())
                session = get_tor_session()
                upper_limit = get_newest_article_id(config.URL_REVIEWS, session)
        else:
            session = requests.session()
            upper_limit = get_newest_article_id(config.URL_REVIEWS, session)

        logger.info(f"Newest article has id: {upper_limit}")

    r = np.arange(lower_limit, upper_limit)

    logger.info(f"Scraping {lower_limit} -> {upper_limit}")
    if random:
        np.random.shuffle(r)

    if tor:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password=load_tor_controll_token())
            scrape_loop(r, output, existing_files, sleep, controller, update=update)
    else:
        scrape_loop(r, output, existing_files, sleep, update=update)

    logger.info("Done.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
