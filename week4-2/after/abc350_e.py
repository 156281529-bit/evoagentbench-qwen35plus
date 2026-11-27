import sys
from decimal import Decimal, getcontext

def solve():
    n, a, x, y = map(int, sys.stdin.buffer.read().split())
    getcontext().prec = 80
    memo = {0: Decimal(0)}
    dx, dy = Decimal(x), Decimal(y)
    def f(v):
        if v in memo: return memo[v]
        via_divide = dx + f(v // a)
        via_roll = (Decimal(6) * dy + sum(f(v // d) for d in range(2, 7))) / Decimal(5)
        memo[v] = min(via_divide, via_roll)
        return memo[v]
    print(f"{f(n):.17g}")

solve()
