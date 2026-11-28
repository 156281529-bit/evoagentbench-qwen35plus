"""Disjoint-swap characterization: https://atcoder.jp/contests/arc195/editorial/12528"""
import sys


def minimum_operations(values):
    # A prefix ends with a single unchanged element or a reversed adjacent pair.
    # The cost is swaps plus the number of equal-value runs in the resulting prefix.
    empty = {None: 0}
    previous = {values[0]: 1}
    two_back = empty
    for left, right in zip(values, values[1:]):
        current = {right: min(cost + (tail != right) for tail, cost in previous.items())}
        if left != right:
            # Append the pair as right, left: one swap and one internal run boundary.
            current[left] = 2 + min(cost + (tail != right) for tail, cost in two_back.items())
        two_back, previous = previous, current
    return min(previous.values())


if __name__ == "__main__":
    numbers = iter(map(int, sys.stdin.buffer.read().split()))
    answers = []
    for _ in range(next(numbers)):
        size = next(numbers)
        answers.append(str(minimum_operations([next(numbers) for _ in range(size)])))
    print("\n".join(answers))
