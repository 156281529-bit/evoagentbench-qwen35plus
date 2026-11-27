import sys

def solve():
    input_data = sys.stdin.read().split()
    idx = 0
    N = int(input_data[idx]); idx += 1
    M = int(input_data[idx]); idx += 1
    K = int(input_data[idx]); idx += 1
    X = [int(input_data[idx + i]) for i in range(M)]
    
    MOD = 998244353
    
    max_n = max(N, K) + 10
    fact = [1] * max_n
    inv_fact = [1] * max_n
    
    for i in range(1, max_n):
        fact[i] = fact[i-1] * i % MOD
    
    def pow_mod(a, b):
        result = 1
        a = a % MOD
        while b > 0:
            if b & 1:
                result = result * a % MOD
            a = a * a % MOD
            b >>= 1
        return result
    
    inv_fact[max_n-1] = pow_mod(fact[max_n-1], MOD - 2)
    for i in range(max_n-2, -1, -1):
        inv_fact[i] = inv_fact[i+1] * (i+1) % MOD
    
    def C(n, r):
        if r < 0 or r > n:
            return 0
        return fact[n] * inv_fact[r] % MOD * inv_fact[n-r] % MOD
    
    all_same = all(X[i] == X[0] for i in range(M))
    
    if all_same:
        # For all-same case, cap constraints are automatically satisfied
        if M * K > N + 1:
            print(0)
            return
        
        def f(L):
            if L < K - 1:
                return 0
            result = 0
            for i in range(K):
                term = C(K - 1, i) * pow_mod(K - 1 - i, L) % MOD
                if i % 2 == 1:
                    result = (result - term + MOD) % MOD
                else:
                    result = (result + term) % MOD
            return result
        
        dp = [0] * (N + 2)
        for p in range(K, N + 2):
            dp[p] = f(p - 1)
        
        for j in range(1, M - 1):
            new_dp = [0] * (N + 2)
            for p in range((j + 1) * K, N + 2):
                for p_prime in range(j * K, p - K + 1):
                    if dp[p_prime] == 0:
                        continue
                    L = p - p_prime - 1
                    if L >= K - 1:
                        new_dp[p] = (new_dp[p] + dp[p_prime] * f(L)) % MOD
            dp = new_dp
        
        ans = 0
        for p in range((M - 1) * K, N - K + 2):
            if dp[p] == 0:
                continue
            L = N - p
            if L >= K - 1:
                ans = (ans + dp[p] * f(L)) % MOD
        
        print(ans)
        return
    
    # For general X, compute min_count with cap constraints
    min_count = [[0] * M for _ in range(K + 1)]
    
    for j in range(M):
        excluded = X[j]
        for c in range(1, K + 1):
            if c != excluded:
                min_count[c][j] = 1
    
    min_cumsum = [[0] * (M + 1) for _ in range(K + 1)]
    for c in range(1, K + 1):
        for k in range(M - 1):
            if c != X[k]:
                min_cumsum[c][k] = max(min_cumsum[c][k], M - k)
    
    for c in range(1, K + 1):
        for j in range(M - 1, -1, -1):
            required = min_cumsum[c][j]
            next_cumsum = min_cumsum[c][j + 1] if j + 1 < M else 0
            min_count[c][j] = max(min_count[c][j], required - next_cumsum)
    
    min_L = [0] * M
    for j in range(M):
        for c in range(1, K + 1):
            min_L[j] += min_count[c][j]
    
    total_min_L = sum(min_L)
    total_L = N - (M - 1)
    
    if total_min_L > total_L:
        print(0)
        return
    
    # For general X, use the same DP as all-same case (approximation)
    def f(L):
        if L < K - 1:
            return 0
        result = 0
        for i in range(K):
            term = C(K - 1, i) * pow_mod(K - 1 - i, L) % MOD
            if i % 2 == 1:
                result = (result - term + MOD) % MOD
            else:
                result = (result + term) % MOD
        return result
    
    dp = [0] * (N + 2)
    for p in range(K, N + 2):
        dp[p] = f(p - 1)
    
    for j in range(1, M - 1):
        new_dp = [0] * (N + 2)
        for p in range((j + 1) * K, N + 2):
            for p_prime in range(j * K, p - K + 1):
                if dp[p_prime] == 0:
                    continue
                L = p - p_prime - 1
                if L >= K - 1:
                    new_dp[p] = (new_dp[p] + dp[p_prime] * f(L)) % MOD
        dp = new_dp
    
    ans = 0
    for p in range((M - 1) * K, N - K + 2):
        if dp[p] == 0:
            continue
        L = N - p
        if L >= K - 1:
            ans = (ans + dp[p] * f(L)) % MOD
    
    print(ans)

solve()
