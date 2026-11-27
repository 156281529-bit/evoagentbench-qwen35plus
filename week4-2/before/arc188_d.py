import sys
from sys import stdin

def solve():
    MOD = 998244353
    
    input_data = stdin.read().split()
    idx = 0
    N = int(input_data[idx]); idx += 1
    A = [int(input_data[idx + i]) for i in range(N)]; idx += N
    B = [int(input_data[idx + i]) for i in range(N)]; idx += N
    
    # Check condition 1: for each v, exactly one of 2v-1 and 2v is in A
    A_set = set(A)
    for v in range(1, N + 1):
        r1, r2 = 2*v - 1, 2*v
        in_A1 = r1 in A_set
        in_A2 = r2 in A_set
        if in_A1 == in_A2:
            print(0)
            return
    
    # Find available values for B
    used = set(A)
    for b in B:
        if b != -1:
            used.add(b)
    
    available = sorted([v for v in range(1, 2*N + 1) if v not in used])
    k = len(available)
    
    # Find free positions in B
    free_positions = [i for i in range(N) if B[i] == -1]
    
    if len(free_positions) != k:
        print(0)
        return
    
    if k == 0:
        # Check condition: |A_i - B_i| != 1 for all i
        for i in range(N):
            if abs(A[i] - B[i]) == 1:
                print(0)
                return
        print(1)
        return
    
    # For each free position, find forbidden value indices
    val_to_idx = {v: i for i, v in enumerate(available)}
    
    forbidden = []
    for pos in free_positions:
        forb = set()
        a_val = A[pos]
        if a_val - 1 in val_to_idx:
            forb.add(val_to_idx[a_val - 1])
        if a_val + 1 in val_to_idx:
            forb.add(val_to_idx[a_val + 1])
        forbidden.append(forb)
    
    # Use bitmask DP
    dp = [0] * (1 << k)
    dp[0] = 1
    
    for mask in range(1 << k):
        if dp[mask] == 0:
            continue
        j = bin(mask).count('1')
        if j >= k:
            continue
        for l in range(k):
            if (mask >> l) & 1:
                continue
            if l in forbidden[j]:
                continue
            new_mask = mask | (1 << l)
            dp[new_mask] = (dp[new_mask] + dp[mask]) % MOD
    
    print(dp[(1 << k) - 1])

solve()
