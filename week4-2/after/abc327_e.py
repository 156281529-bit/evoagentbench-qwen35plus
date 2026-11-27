import math
import sys


def rating(scores):
    n = len(scores)
    best = [0.0] * (n + 1)
    for i, score in enumerate(scores, 1):
        for k in range(i, 0, -1):
            best[k] = max(best[k], 0.9 * best[k - 1] + score)
    denominator = 0.0
    answer = -math.inf
    for k in range(1, n + 1):
        denominator = 1 + denominator * 0.9
        answer = max(answer, best[k] / denominator - 1200 / math.sqrt(k))
    return answer


if __name__ == "__main__":
    _, *scores = map(int, sys.stdin.read().split())
    print(f"{rating(scores):.15f}")
