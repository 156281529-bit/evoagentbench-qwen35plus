import math

def solve():
    N = int(input())
    P = list(map(int, input().split()))
    
    # best[j] = max weighted sum for choosing j contests
    # When we add a contest as the j-th contest, it gets weight 1.0
    # and all previous j-1 contests get their weights multiplied by 0.9
    best = [0.0] * (N + 1)
    
    for i in range(N):
        p = P[i]
        # Update dp values for this contest, going backwards to avoid using updated values
        for j in range(i + 1, 0, -1):
            if j == 1:
                dp_j = float(p)
            else:
                dp_j = p + 0.9 * best[j - 1]
            best[j] = max(best[j], dp_j)
    
    max_rating = float('-inf')
    
    for k in range(1, N + 1):
        # Denominator: sum of (0.9)^{k-i} for i=1 to k = 10 * (1 - 0.9^k)
        denominator = 10.0 * (1.0 - 0.9 ** k)
        weighted_sum = best[k]
        rating = weighted_sum / denominator - 1200.0 / math.sqrt(k)
        max_rating = max(max_rating, rating)
    
    print(max_rating)

solve()