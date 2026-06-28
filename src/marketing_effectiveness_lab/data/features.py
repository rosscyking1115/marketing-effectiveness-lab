"""Canonical derivations for shared weekly modeling features.

These functions are the single source of truth for the seasonal, holiday, and
promotion indicator columns so the demo generator and the connector assembly
pipeline encode them identically. Keeping them here prevents the two data paths
from drifting apart (e.g. a model trained on demo data seeing a different
seasonal encoding than connector-assembled data).

Each helper accepts an array-like (a pandas ``Series``/``Index`` or a NumPy
array) and returns the same kind of object, preserving the pandas index when one
is supplied so the result can be assigned back to a frame without misalignment.
"""

from __future__ import annotations

# A promotion is treated as active once the weekly discount depth reaches this
# threshold. Connector data only exposes discount depth, so the flag is derived
# from it on both paths.
PROMOTION_DEPTH_THRESHOLD_PCT = 5.0

# November and December capture the peak UK retail trading period.
HOLIDAY_MONTHS = (11, 12)

# Spring/summer spans March through August; the remaining months are autumn/
# winter. The two seasonal flags are exact complements so every week belongs to
# exactly one season (no week is left with both flags set to zero).
SPRING_SUMMER_MONTHS = (3, 4, 5, 6, 7, 8)


def season_spring_summer_flag(month):
    """Return 1 for spring/summer months (March-August), else 0."""

    return month.isin(SPRING_SUMMER_MONTHS).astype(int)


def season_autumn_winter_flag(month):
    """Return 1 for autumn/winter months, as the complement of spring/summer."""

    return (1 - season_spring_summer_flag(month)).astype(int)


def holiday_flag(month):
    """Return 1 for peak holiday trading months (November-December), else 0."""

    return month.isin(HOLIDAY_MONTHS).astype(int)


def promotion_flag(promotion_depth_pct):
    """Return 1 where weekly discount depth meets the promotion threshold."""

    return (promotion_depth_pct >= PROMOTION_DEPTH_THRESHOLD_PCT).astype(int)
