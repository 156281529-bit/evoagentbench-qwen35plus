import sys
from collections import defaultdict

def solve():
    data = sys.stdin.read().split()
    
    idx = 0
    N = int(data[idx]); idx += 1
    M = int(data[idx]); idx += 1
    
    # Build adjacency list: incoming[v] = list of (u, beauty, cost)
    incoming = defaultdict(list)
    for i in range(M):
        u = int(data[idx]); idx += 1
        v = int(data[idx]); idx += 1
        b = int(data[idx]); idx += 1
        c = int(data[idx]); idx += 1
        incoming[v].append((u, b, c))
    
    def check(x):
        """Check if there exists a path with ratio >= x"""
        # dp[v] = max sum of (b - x*c) for path from 1 to v
        dp = [-float('inf')] * (N + 1)
        dp[1] = 0
        
        # Process vertices in order (DAG property: u < v)
        for v in range(2, N + 1):
            for u, b, c in incoming[v]:
                if dp[u] != -float('inf'):
                    dp[v] = max(dp[v], dp[u] + b - x * c)
        
        return dp[N] >= 0
    
    # Binary search for maximum ratio
    left, right = 0.0, 10000.0  # max possible ratio is 10^4 (max beauty / min cost)
    
    # 100 iterations gives sufficient precision
    for _ in range(100):
        mid = (left + right) / 2
        if check(mid):
            left = mid
        else:
            right = mid
    
    print(f"{left:.16f}")

solve()