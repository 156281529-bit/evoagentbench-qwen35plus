import sys
from decimal import Decimal, localcontext


def optimum(n, edges):
    # Dinkelbach iteration: each trial maximizes B*q - C*p over DAG paths.
    outgoing = [[] for _ in range(n)]
    for u, v, beauty, cost in edges:
        outgoing[u - 1].append((v - 1, beauty, cost))
    p, q = 0, 1
    while True:
        scores = [None] * n
        path_cost = [0] * n
        scores[0] = 0
        for u, neighbors in enumerate(outgoing):
            base = scores[u]
            if base is None:
                continue
            for v, beauty, cost in neighbors:
                score = base + beauty * q - cost * p
                if scores[v] is None or score > scores[v]:
                    scores[v] = score
                    path_cost[v] = path_cost[u] + cost
        residual, cost = scores[-1], path_cost[-1]
        if residual == 0:
            return p, q
        p, q = (residual + cost * p) // q, cost


if __name__ == "__main__":
    data = iter(map(int, sys.stdin.read().split()))
    n, m = next(data), next(data)
    p, q = optimum(n, [tuple(next(data) for _ in range(4)) for _ in range(m)])
    with localcontext() as context:
        context.prec = 60
        print(f"{Decimal(p) / Decimal(q):.16f}")
