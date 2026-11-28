"""Parity DP using the exchange bound in https://atcoder.jp/contests/abc400/editorial/12637."""
import sys


def best_price(cakes, pairs):
    cakes.sort(key=max, reverse=True)
    needed = 2 * pairs
    impossible = (-10**18,) * 4
    # best[gap][mask]: selected min(processed, needed) - gap cakes.
    # Bits track parity of X and Y; the selected count determines Z's parity.
    best = [(0, *impossible[1:]), impossible, impossible]
    for index, (x, y, z) in enumerate(cakes):
        new = []
        for gap in range(3):
            if index < needed:
                take = best[gap]
                skip = best[gap - 1] if gap else impossible
            else:
                take = best[gap + 1] if gap < 2 else impossible
                skip = best[gap]
            new.append(tuple(max(skip[mask], take[mask] + z, take[mask ^ 1] + x, take[mask ^ 2] + y)
                             for mask in range(4)))
        best = new
    return best[0][0]


if __name__ == "__main__":
    data = iter(map(int, sys.stdin.buffer.read().split()))
    answers = []
    for _ in range(next(data)):
        n, k = next(data), next(data)
        rows = [(next(data), next(data), next(data)) for _ in range(n)]
        answers.append(str(best_price(rows, k)))
    print("\n".join(answers))
