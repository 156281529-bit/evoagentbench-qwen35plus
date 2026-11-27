"""Constant-size residual tile graph after the ABC382 G editorial reductions."""
import sys
from collections import deque
from functools import lru_cache


def neighbors(k, i, j, strip):
    horizontal = (i + j) % 2 == 0
    for step in (-1, 1):
        edge = k - 1 if step < 0 else 0
        if horizontal:
            yield i + step, j, edge
        else:
            yield i, j + step, edge
        adjacent = strip + step
        if 0 <= adjacent < k:
            yield i, j, adjacent
        else:
            for index in range(k):
                if horizontal:
                    yield i, j + step, index
                else:
                    yield i + step, j, index


@lru_cache(None)
def residual_table(k, start):
    origin = (0, 0, start)
    queue = deque([origin])
    distance = {origin: 0}
    blocks = [(0, 0), (1, 1)] + [(x, 0) for x in range(1, 4)] + [(0, y) for y in range(1, 4)]
    wanted = {(i, j, z) for i, j in blocks for z in range(k)}
    result = {}
    while wanted:
        tile = queue.popleft()
        if tile in wanted:
            wanted.remove(tile)
            result[tile] = distance[tile]
        for adjacent in neighbors(k, *tile):
            if adjacent not in distance:
                distance[adjacent] = distance[tile] + 1
                queue.append(adjacent)
    return result


def strip_index(index, k):
    if k <= 6 or index < 3:
        return index
    return max(3, 6 - (k - index))


def distance(k, sx, sy, tx, ty):
    i, j = sx // k, sy // k
    if (i + j) % 2:
        sx, sy, tx, ty = sy, sx, ty, tx
        i, j = j, i
    dx, dy = tx // k - i, ty // k - j
    horizontal_end = (dx + dy) % 2 == 0
    start = sy % k
    end = (ty if horizontal_end else tx) % k
    if dx == dy == 0:
        return min(abs(start - end), 2)
    if dy < 0:
        start = k - 1 - start
    if (horizontal_end and dy < 0) or (not horizontal_end and dx < 0):
        end = k - 1 - end
    dx, dy = abs(dx), abs(dy)
    diagonal = min(dx, dy) - int(dx == dy)
    dx -= diagonal
    dy -= diagonal
    pairs = max(0, (max(dx, dy) - 2) // 2)
    if dx > dy:
        dx -= 2 * pairs
    else:
        dy -= 2 * pairs
    base = residual_table(min(k, 6), strip_index(start, k))[dx, dy, strip_index(end, k)]
    return 2 * diagonal + (3 if k == 2 else 4) * pairs + base


if __name__ == "__main__":
    tokens = iter(map(int, sys.stdin.buffer.read().split()))
    answers = [str(distance(*(next(tokens) for _ in range(5)))) for _ in range(next(tokens))]
    print("\n".join(answers))

