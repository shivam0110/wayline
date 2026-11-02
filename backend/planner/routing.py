from bisect import bisect_left
from math import asin, ceil, cos, floor, hypot, pi, radians, sin, sqrt

MILE = 1609.344


def distance(a, b):
    lon1, lat1, lon2, lat2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371008.8 * 2 * asin(min(1, sqrt(h)))


def cumulative(points):
    result = [0.0]
    for a, b in zip(points, points[1:]):
        result.append(result[-1] + distance(a, b))
    return result


def sample_route(route, interval):
    points = route["geometry"]
    lengths = cumulative(points)
    total = lengths[-1]
    if total < 50 or route["distance_meters"] < 50:
        raise ValueError("Choose different locations at least 50 meters apart.")
    # Provider road mileage is authoritative; geographic length locates samples on the polyline.
    road_total = route["distance_meters"]
    targets = [i * interval * MILE for i in range(ceil(road_total / (interval * MILE)))] + [road_total]
    times = route.get("vertex_seconds")
    if not times or len(times) != len(points):
        times = [value / total * route["duration_seconds"] for value in lengths]
    checkpoints, indices = [], []
    for target in targets:
        position = target / road_total * total
        i = max(1, min(bisect_left(lengths, position), len(points) - 1))
        fraction = (position - lengths[i - 1]) / (lengths[i] - lengths[i - 1]) if lengths[i] != lengths[i - 1] else 0
        coordinate = [points[i - 1][j] + (points[i][j] - points[i - 1][j]) * fraction for j in (0, 1)]
        checkpoints.append({"coordinate": coordinate, "mile": target / MILE, "elapsed_seconds": times[i - 1] + (times[i] - times[i - 1]) * fraction})
        indices.append(i)
    segments = []
    for i, (a, b) in enumerate(zip(checkpoints, checkpoints[1:])):
        middle = points[indices[i]:indices[i + 1]]
        stride = max(1, ceil(len(middle) / 180))
        segments.append({"coordinates": [a["coordinate"], *middle[::stride], b["coordinate"]], "miles": b["mile"] - a["mile"]})
    return checkpoints, segments


def corridor_grid(routes, buffer_miles=25, limit=120):
    points = [p for route in routes for p in route]
    lat = sum(p[1] for p in points) / len(points)
    scale_x, scale_y = 69.0934 * cos(radians(lat)), 69.0934
    if max(p[0] for p in points) - min(p[0] for p in points) > 180:
        raise ValueError("Trips crossing the date line are outside this demo's supported area.")
    lines = [[(p[0] * scale_x, p[1] * scale_y) for p in route] for route in routes]
    edges = [(a, b) for line in lines for a, b in zip(line, line[1:])]
    xs, ys = [p[0] * scale_x for p in points], [p[1] * scale_y for p in points]
    xmin, xmax, ymin, ymax = min(xs) - buffer_miles, max(xs) + buffer_miles, min(ys) - buffer_miles, max(ys) + buffer_miles

    def near(x, y, radius):
        for (ax, ay), (bx, by) in edges:
            if x < min(ax, bx) - radius or x > max(ax, bx) + radius or y < min(ay, by) - radius or y > max(ay, by) + radius:
                continue
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))) if dx or dy else 0
            if hypot(x - ax - t * dx, y - ay - t * dy) <= radius:
                return True
        return False

    size = max(12, sqrt((xmax - xmin) * (ymax - ymin) / 450))
    for _ in range(30):
        cells = []
        for ix in range(floor(xmin / size), ceil(xmax / size)):
            for iy in range(floor(ymin / size), ceil(ymax / size)):
                x, y = (ix + .5) * size, (iy + .5) * size
                if near(x, y, buffer_miles + size * .71):
                    west, east, south, north = ix * size / scale_x, (ix + 1) * size / scale_x, iy * size / scale_y, (iy + 1) * size / scale_y
                    cells.append({"coordinate": [x / scale_x, y / scale_y], "polygon": [[west, south], [east, south], [east, north], [west, north], [west, south]]})
        if len(cells) <= limit:
            return cells, size
        size *= 1.2
    raise ValueError("This corridor is too large. Choose a shorter trip.")
