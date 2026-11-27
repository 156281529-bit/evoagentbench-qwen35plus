import sys
sys.setrecursionlimit(200000)

def solve():
    data = sys.stdin.read().split()
    N, A, X, Y = int(data[0]), int(data[1]), int(data[2]), int(data[3])
    
    memo = {}
    
    def E(n):
        if n == 0:
            return 0.0
        if n in memo:
            return memo[n]
        
        # Option 1: Pay X, divide by A
        option1 = X + E(n // A)
        
        # Option 2: Pay Y, roll die
        # E(n) = Y + (1/6)*E(n) + (1/6)*sum_{b=2}^{6} E(n//b)
        # Solving: E(n) = (6*Y + sum_{b=2}^{6} E(n//b)) / 5
        sum_die = sum(E(n // b) for b in range(2, 7))
        option2 = (6 * Y + sum_die) / 5
        
        result = min(option1, option2)
        memo[n] = result
        return result
    
    print(f"{E(N):.15f}")

solve()