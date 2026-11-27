import math
import sys

MOD = 998244353


def completions(a, b):
    n = len(a)
    by_block = {((rank - 1) // 2): i for i, rank in enumerate(a)}
    if len(by_block) != n:
        return 0
    following = [-1] * n
    has_previous = [False] * n
    for i, rank in enumerate(b):
        if rank == -1:
            continue
        j = by_block[(rank - 1) // 2]
        if a[j] == rank or has_previous[j]:
            return 0
        following[i] = j
        has_previous[j] = True

    seen = [False] * n
    paths = [0] * 4
    for start in sorted(range(n), key=has_previous.__getitem__):
        if seen[start]:
            continue
        mask = 0
        node = start
        while node != -1 and not seen[node]:
            seen[node] = True
            mask |= 1 << (a[node] % 2)
            node = following[node]
        if node == -1:
            paths[mask] += 1
        elif mask != 3:
            return 0

    # Labeled permutations are sets of cycles. Excluding all-white and
    # all-black cycles multiplies their generating function by (1-w)(1-b).
    white, black, mixed = paths[1:]
    total = white + black + mixed
    factorial = [1] * (total + 1)
    for i in range(1, total + 1):
        factorial[i] = factorial[i - 1] * i % MOD
    answer = factorial[total]
    if total:
        answer -= (white + black) * factorial[total - 1]
    if total >= 2:
        answer += white * black * factorial[total - 2]
    return answer % MOD


if __name__ == "__main__":
    n, *data = map(int, sys.stdin.read().split())
    print(completions(data[:n], data[n:]))
