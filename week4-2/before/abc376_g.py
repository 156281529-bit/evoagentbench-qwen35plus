# YOUR CODE HERE
import sys
from heapq import heappush, heappop

MOD = 998244353

def mod_inverse(a, mod=MOD):
    return pow(a, mod - 2, mod)

def solve():
    input_data = sys.stdin.read().split()
    idx = 0
    T = int(input_data[idx])
    idx += 1
    
    results = []
    
    for _ in range(T):
        N = int(input_data[idx])
        idx += 1
        
        parents = [int(input_data[idx + i]) for i in range(N)]
        idx += N
        
        a = [int(input_data[idx + i]) for i in range(N)]
        idx += N
        
        # Build adjacency list (children of each vertex)
        # vertices are 0 to N, where 0 is root
        children = [[] for _ in range(N + 1)]
        for i in range(N):
            p = parents[i]
            vertex = i + 1  # vertex i+1 has parent p
            children[p].append(vertex)
        
        # Simulate search process using priority queue
        # Priority: (-a[u-1], u) for max-heap behavior (pick highest a[u] first)
        pq = []
        for v in children[0]:
            heappush(pq, (-a[v - 1], v))
        
        step = {}
        time = 0
        
        while pq:
            _, u = heappop(pq)
            time += 1
            step[u] = time
            for v in children[u]:
                heappush(pq, (-a[v - 1], v))
        
        # Compute expected value: sum(a_i * step_i) / sum(a_i)
        numerator = 0
        S = sum(a)
        for i in range(1, N + 1):
            numerator = (numerator + a[i - 1] * step[i]) % MOD
        
        S_inv = mod_inverse(S % MOD)
        answer = numerator * S_inv % MOD
        results.append(answer)
    
    for r in results:
        print(r)

solve()