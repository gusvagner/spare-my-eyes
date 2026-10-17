import math
from collections.abc import Sequence

Point = tuple[float, float]


def eye_aspect_ratio(contour: Sequence[Point]) -> float:
    if len(contour) != 6:
        raise ValueError(f"Eye contour needs 6 points (p1..p6), got {len(contour)}: {contour!r}")
    p1, p2, p3, p4, p5, p6 = contour
    width = math.dist(p1, p4)
    if width == 0:
        raise ValueError(f"Eye corners p1 and p4 coincide at {p1!r}; expected distinct points")
    return (math.dist(p2, p6) + math.dist(p3, p5)) / (2 * width)


def iris_diameter(boundary: Sequence[Point]) -> float:
    if len(boundary) != 4:
        raise ValueError(
            f"Iris boundary needs 4 points (right, top, left, bottom), got {len(boundary)}: "
            f"{boundary!r}"
        )
    right, top, left, bottom = boundary
    return (math.dist(right, left) + math.dist(top, bottom)) / 2


def yaw_degrees(rotation: Sequence[Sequence[float]]) -> float:
    if len(rotation) != 3 or any(len(row) != 3 for row in rotation):
        raise ValueError(f"Rotation must be a 3x3 matrix, got {rotation!r}")
    return math.degrees(math.atan2(rotation[0][2], rotation[2][2]))
