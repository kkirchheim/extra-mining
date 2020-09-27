# -*- coding: utf-8 -*-
"""

"""
import os
import json
import numpy as np
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

this_dir = os.path.dirname(__file__)

URL_WEBSITE = "https://www.xxx.de"
URL_REVIEWS = URL_WEBSITE + "/rezensionen"

DIR_ROOT = os.path.abspath(os.path.join(this_dir, ".."))
DIR_DATA = os.path.join(DIR_ROOT, "data")

DIR_RAW = os.path.join(DIR_DATA, "raw")
DIR_RAW_HTML = os.path.join(DIR_RAW, "html")
DIR_RAW_DNB = os.path.join(DIR_RAW, "dnb-cache")

DIR_PROCESSED = os.path.join(DIR_DATA, "processed")
DIR_INTERIM = os.path.join(DIR_DATA, "interim")
DIR_REPORT = os.path.join(DIR_DATA, "report")
DIR_EXTERNAL = os.path.join(DIR_DATA, "external")

DIR_RESOURCES = os.path.join(DIR_ROOT, "resources")

PATH_STOP_WORDS = os.path.join(DIR_RESOURCES, "stopwords.txt")
PATH_IGNORE_URLS = os.path.join(DIR_RESOURCES, "ignore-urls.txt")
PATH_CITIES = os.path.join(DIR_RESOURCES, "german-cities.txt")
PATH_TITLES = os.path.join(DIR_RESOURCES, "titles.txt")

enddate = np.datetime64("2020-01-01")
startdate = np.datetime64("2001-01-01")


def load_secret_dnb():
    return load_secret("dnb-access-token")


def load_secret(key):
    with open(os.path.join(DIR_DATA, "secrets.json"), "r") as f:
        secrets = json.load(f)
        dnb_token = secrets[key]
    return dnb_token


# cluster for topics to evaluate over time
topic_clusters = {
    "Kind": ["Kind", "Jugend", "Prävention", "Psychotherapie", "Eltern", "Schule", "Jugendhilfe", "Psychoanalyse", "Familie", "Psychische Störung"],
    "Krankenhaus": ["Krankenhaus", "Altenpflege", "Demenz", "Management", "Gesundheitswesen", "Krankenpflege Qualitätsmanagement", "Sozialeinrichtung", "Gesundheitsförderung", "Führung"],
    "Soziale Ungleichheit": ["Soziale Ungleichheit", "Armut", "Sozialpolitik", "Europa", "Gesellschaft", "Europäische Union", "Gesundheit", "Demokratie", "Sozialstaat", "Globalisierung"],
    "Sozialarbeit": ["Sozialarbeit", "Sozialpädagogik", "Pädagogik", "Soziale Arbeit", "Professionalisierung", "Erwachsenenbildung", "Soziologie", "Ethik", "Forschung", "Theorie"],
    "Migration": ["Migration", "Soziale Integration", "Alltag", "Migrationshintergrund", "Einwanderer", "Flüchtling", "Identität", "Lebenswelt", "Integration", "Berufliche Integration"],
    "Kindertagesstätte": ["Kindertagesstätte", "Bildung", "Evaluation", "Kooperation", "Grundschule", "Kleinkindpädagogik", "Vorschulerziehung", "Inklusive Pädagogik", "Erlebnispädagogik", "Chancengleichheit"],
    "Alter": ["Alter", "Sozialraum", "Ehrenamtliche Tätigkeit", "Stadt", "Altern", "Stadtentwicklung", "Bevölkerungsentwicklung", "Deutschland", "Lebensführung", "Pflegebedürftigkeit"],
    "Frau": ["Frau", "Sozialer Wandel", "Geschlechterrolle", "Mann", "Geschlechtsunterschied", "Geschlechterforschung", "Männlichkeit", "Soziologische Theorie", "Soziale Konstruktion", "Feminismus"],
    "Geschichte": ["Geschichte", "Psychologie", "Psychiatrie", "Betreuungsrecht", "Biografie", "Psychisch Kranker", "Philosophie", "Nationalsozialismus", "Diskursanalyse", "Psychosomatik"],
    "Medienpädagogik": ["Medienpädagogik", "Soziales Netzwerk", "Internet", "Neue Medien", "Medien", "Drogenkonsum", "Medienkompetenz", "Einfühlung", "Medienkonsum", "Kommunikationsverhalten"],
}

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '[%(levelname)s][%(processName)s] %(asctime)s - %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',  # Default is stderr
        },
    },
    'loggers': {
        'utils': {  # root logger
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        },
        '': {  # root logger
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        },
        '__main__': {  # if __name__ == '__main__'
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        },
    }
}
