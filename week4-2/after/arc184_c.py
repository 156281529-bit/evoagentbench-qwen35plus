import sys


def scores(offsets):
    """Best mountain count for each of the four residues of the shift."""
    if len(offsets) <= 1:
        if not offsets:
            return [0] * 4
        return [int((shift + offsets[0]) % 4 != 1) for shift in range(4)]
    counts = [0] * 4
    halves = [[], []]
    for value in offsets:
        counts[value % 4] += 1
        halves[value % 2].append(value // 2)
    child = [scores(group) for group in halves]
    result = []
    for shift in range(4):
        parity = shift % 2
        next_parity = ((shift + 1) // 2) % 2
        best = max(child[parity][next_parity::2])
        result.append(counts[(3 - shift) % 4] + best)
    return result


if __name__ == "__main__":
    _, *values = map(int, sys.stdin.read().split())
    print(max(scores(values)))
