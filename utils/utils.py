import os
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path


# region Compare data
def levenstein_distance_case_insensitive(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings in a case-insensitive manner.
    :param s1: First string
    :param s2: Second string
    :return: Levenshtein distance
    """
    return levenstein_distance(s1.lower(), s2.lower())


def levenstein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings.
    :param s1: First string
    :param s2: Second string
    :return: Levenshtein distance
    """
    if len(s1) < len(s2):
        return levenstein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def matching_words_count(s1: str, s2: str) -> int:
    """
    Count the number of matching words between two strings.
    :param s1: First string
    :param s2: Second string
    :return: Number of matching words
    """
    words1 = set(s1.lower().split())
    words2 = set(s2.lower().split())
    return len(words1.intersection(words2))


def calculate_coordinate_distance_cm(lat_1: float, lon_1: float, lat_2: float, lon_2: float) -> float:
    """
    Find approximate distance between two coordinates using Haversine formula.
    :param lat_1: Latitude of first point
    :param lon_1: Longitude of first point
    :param lat_2: Latitude of second point
    :param lon_2: Longitude of second point
    :return: Distance in cm
    """

    # Radius of the Earth in cm
    R = 6371 * 1000 * 100  # 6371 km to cm

    dlat = radians(lat_2 - lat_1)
    dlon = radians(lon_2 - lon_1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat_1)) * cos(radians(lat_2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


# endregion
