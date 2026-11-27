MOD = 998244353

def solve():
    import sys
    input = sys.stdin.readline
    
    N = int(input())
    A = list(map(int, input().split()))
    
    # Precompute factorials for binomial coefficients
    MAX = 2 * N + 5
    fact = [1] * MAX
    inv = [1] * MAX
    finv = [1] * MAX
    
    for i in range(2, MAX):
        fact[i] = fact[i-1] * i % MOD
        inv[i] = (MOD - MOD // i) * inv[MOD % i] % MOD
        finv[i] = finv[i-1] * inv[i] % MOD
    
    def binom(n, k):
        if k < 0 or k > n or n < 0:
            return 0
        return fact[n] * finv[k] % MOD * finv[n-k] % MOD
    
    def sum_f(k, t_min, t_max):
        # Sum of f(k, t) for t in [t_min, t_max]
        # f(k, t) = number of valid completions with k positions remaining and prefix sum t
        # Formula derived from telescoping sum of binomial coefficients
        if t_min > t_max:
            return 0
        
        n1 = 2 * k - t_min - 1
        n2 = 2 * k - t_max - 2
        
        term1 = binom(n1, k)
        term2 = binom(n1, k + 1)
        term3 = binom(n2, k)
        term4 = binom(n2, k + 1)
        
        return (term1 - term2 - term3 + term4 + 2 * MOD) % MOD
    
    count = 0
    s = 0  # Current prefix sum
    
    for i in range(N):
        k = N - i - 1  # Remaining positions
        t_min = max(0, s - 1)
        t_max = s + A[i] - 2
        
        if k > 0:
            # Sum f(k, t) for valid t values
            count = (count + sum_f(k, t_min, t_max)) % MOD
        else:  # k = 0, last position
            # Add 1 if choosing v = s gives valid ending (prefix sum becomes -1)
            if 0 <= s < A[i]:
                count = (count + 1) % MOD
        
        s = s + A[i] - 1
        
        # Check if prefix is still valid (prefix sum must be >= 0 until the end)
        if i < N - 1 and s < 0:
            break
    else:
        # If we completed the loop and final prefix sum is -1, A itself is valid
        if s == -1:
            count = (count + 1) % MOD
    
    print(count)

solve()