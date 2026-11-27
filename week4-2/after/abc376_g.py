import heapq
import sys

MOD = 998244353


class Block:
    def __init__(self, node, weight, size):
        self.node, self.weight, self.size = node, weight, size

    def __lt__(self, other):
        return self.weight * other.size > other.weight * self.size


def expected_cost(parent, weights):
    n = len(parent) - 1
    representative = list(range(n + 1))
    size = [0] + [1] * n
    total = sum(weights)
    numerator = total
    queue = [Block(i, weights[i], 1) for i in range(1, n + 1)]
    heapq.heapify(queue)
    while queue:
        block = heapq.heappop(queue)
        i = block.node
        if representative[i] != i or size[i] != block.size:
            continue
        p = parent[i]
        while representative[p] != p:
            representative[p] = representative[representative[p]]
            p = representative[p]
        numerator += size[p] * weights[i]
        representative[i] = p
        size[p] += size[i]
        weights[p] += weights[i]
        if p:
            heapq.heappush(queue, Block(p, weights[p], size[p]))
    return numerator * pow(total, -1, MOD) % MOD


if __name__ == "__main__":
    data = iter(map(int, sys.stdin.read().split()))
    for _ in range(next(data)):
        n = next(data)
        parent = [0] + [next(data) for _ in range(n)]
        weights = [0] + [next(data) for _ in range(n)]
        print(expected_cost(parent, weights))
