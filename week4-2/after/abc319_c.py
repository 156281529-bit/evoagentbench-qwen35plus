from decimal import Decimal, getcontext
from math import factorial
import sys


def probability(grid):
    lines = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
             (2, 5, 8), (0, 4, 8), (2, 4, 6)]
    pairs = [[] for _ in grid]
    for line in lines:
        for pos in line:
            a, b = (i for i in line if i != pos)
            if grid[a] == grid[b] != grid[pos]:
                pairs[pos].append((1 << a) | (1 << b))
    ways = [0] * 512
    ways[0] = 1
    for mask in range(511):
        for i, constraints in enumerate(pairs):
            if not mask & (1 << i) and all(mask & pair != pair for pair in constraints):
                ways[mask | (1 << i)] += ways[mask]
    return Decimal(ways[-1]) / factorial(9)


if __name__ == "__main__":
    getcontext().prec = 70
    print(f"{probability(list(map(int, sys.stdin.read().split()))):.30f}")
