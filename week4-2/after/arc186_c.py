import heapq
import sys


def max_gain(boxes, colors):
    boxes.sort(reverse=True)
    suffix_gain = sum(max(0, volume - price) for volume, price in boxes)
    prefix_cost = 0
    cheap = []
    best = 0
    for volume, price in boxes:
        suffix_gain -= max(0, volume - price)
        if len(cheap) == colors - 1:
            best = max(best, suffix_gain + volume - price - prefix_cost)
        cost = price - 1
        heapq.heappush(cheap, -cost)
        prefix_cost += cost
        if len(cheap) >= colors:
            prefix_cost += heapq.heappop(cheap)
    return best


if __name__ == "__main__":
    data = iter(map(int, sys.stdin.read().split()))
    for _ in range(next(data)):
        n, colors = next(data), next(data)
        boxes = [(next(data), next(data)) for _ in range(n)]
        print(max_gain(boxes, colors))
