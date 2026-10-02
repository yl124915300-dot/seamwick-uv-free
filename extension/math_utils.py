# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 yulei
"""Area math extracted from the existing Seamwick UV source."""

import math


def polygon_area_2d(points):
    """Unsigned shoelace area of a UV polygon."""
    if len(points) < 3:
        return 0.0
    twice = sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )
    return abs(twice) * 0.5


def polygon_area_3d(points):
    """Newell area of a planar polygon, including world-space scale."""
    if len(points) < 3:
        return 0.0
    x = y = z = 0.0
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        x += point[1] * following[2] - point[2] * following[1]
        y += point[2] * following[0] - point[0] * following[2]
        z += point[0] * following[1] - point[1] * following[0]
    return 0.5 * math.sqrt(x * x + y * y + z * z)


def area_match_scale(world_area, uv_area, epsilon=1e-12):
    """UV scale required for one UV-area unit per world-area unit."""
    if not (math.isfinite(world_area) and math.isfinite(uv_area)):
        raise ValueError("Non-finite surface or UV area")
    if world_area <= epsilon or uv_area <= epsilon:
        raise ValueError("Degenerate surface or UV area")
    return math.sqrt(world_area / uv_area)
