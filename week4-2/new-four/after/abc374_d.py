"""Compute a shortest laser route with the 64-bit significand of extended precision."""
import sys
from decimal import Decimal, localcontext
from functools import lru_cache
from math import frexp


@lru_cache(maxsize=64)
def unit(exponent):
    return Decimal(2) ** exponent


def extended(value):
    if not value:
        return value
    exponent = frexp(float(value))[1] - 1
    if value < unit(exponent):
        exponent -= 1
    step = unit(exponent - 63)
    return (value / step).to_integral_value() * step


def optimum(segments, speed, laser):
    points = [p for seg in segments for p in seg] + [(0, 0)]
    n = len(segments)
    lengths = [[extended(Decimal((x-u)**2 + (y-v)**2).sqrt())
                for u, v in points] for x, y in points]
    transit = [[extended(distance / speed) for distance in row] for row in lengths]
    drawing = [extended(lengths[2*i][2*i+1] / laser) for i in range(n)]
    # After a subset is printed only the current endpoint affects future travel.
    states = [{} for _ in range(1 << n)]
    states[0][2*n] = Decimal(0)
    for mask, endpoints in enumerate(states):
        for endpoint, elapsed in endpoints.items():
            for i, draw in enumerate(drawing):
                if mask & (1 << i):
                    continue
                target = states[mask | (1 << i)]
                for start in (2*i, 2*i+1):
                    time = extended(extended(elapsed + transit[endpoint][start]) + draw)
                    finish = start ^ 1
                    if finish not in target or time < target[finish]:
                        target[finish] = time
    return min(states[-1].values())


if __name__ == "__main__":
    data = iter(map(int, sys.stdin.buffer.read().split()))
    size, speed, laser = next(data), next(data), next(data)
    segments = [((next(data), next(data)), (next(data), next(data))) for _ in range(size)]
    with localcontext() as context:
        context.prec = 100
        print(f"{optimum(segments, speed, laser):.20f}")
