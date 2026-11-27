# YOUR CODE HERE
import sys

def solve():
    data = sys.stdin.read().split()
    N = int(data[0])
    A = [int(data[i+1]) for i in range(N)]
    
    def g(j):
        """Returns 1 if j-th crease (1-indexed) is a mountain fold, 0 otherwise.
        
        The paperfolding sequence: g(n) = 1 if v_2(n) is even, else 0.
        where v_2(n) is the 2-adic valuation (number of trailing zeros in binary).
        """
        if j <= 0:
            return 0
        lowbit = j & -j
        v2 = lowbit.bit_length() - 1
        return 1 if v2 % 2 == 0 else 0
    
    # Find max f(i) where f(i) = sum_k g(i + A_k)
    candidates = set()
    
    # Check small values of i
    for i in range(1, 300000):
        candidates.add(i)
    
    # Check critical points where v_2(i + A_k) changes
    for Ak in A:
        for b in range(0, 33):
            mod = 1 << b
            if mod == 0:
                continue
            base = ((-Ak) % mod + mod) % mod
            for delta in range(-5, 6):
                i = base + delta * mod
                if i >= 1:
                    candidates.add(i)
    
    max_f = 0
    for i in candidates:
        f_i = sum(g(i + Ak) for Ak in A)
        max_f = max(max_f, f_i)
    
    print(max_f)

if __name__ == "__main__":
    solve()