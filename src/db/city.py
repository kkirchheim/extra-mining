# -*- coding: utf-8 -*-
"""

"""


class City(object):
    NAME = "name"
    LNG = "lng"
    LAT = "lat"

    def __init__(self, name, lng=None, lat=None):
        self.lng = lng
        self.lat = lat
        self.name = name
