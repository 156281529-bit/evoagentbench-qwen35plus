import sys

MOD = 998244353


def count(n, alphabet, target):
    # cover[length] counts words that contain every one of the other symbols.
    symbols = alphabet - 1
    distinct = [1] + [0] * symbols
    cover = [distinct[-1]]
    for _ in range(n):
        distinct = [(used * ways + (symbols - used + 1) * distinct[used - 1]) % MOD
                    if used else 0 for used, ways in enumerate(distinct)]
        cover.append(distinct[-1])

    # Split before the first target symbol. For unequal neighbors there is
    # also a last occurrence of the next symbol after the full cover.
    equal = [0] + cover[:n]
    unequal = [0] * (n + 1)
    for length in range(2, n + 1):
        unequal[length] = (cover[length - 2] + (alphabet - 2) * unequal[length - 1]) % MOD

    ways = cover
    for left, right in zip(reversed(target[:-1]), reversed(target[1:])):
        block = equal if left == right else unequal
        updated = [0] * (n + 1)
        for size, choices in enumerate(block):
            if choices:
                for length in range(n - size + 1):
                    updated[length + size] += choices * ways[length]
        ways = [value % MOD for value in updated]
    return ways[n]


if __name__ == "__main__":
    n, m, k, *target = map(int, sys.stdin.read().split())
    print(count(n, k, target))
