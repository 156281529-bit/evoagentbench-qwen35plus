class Solution:
    def count(self, num1: str, num2: str, min_sum: int, max_sum: int) -> int:
        MOD = 10**9 + 7
        
        def countUpTo(num: str) -> int:
            n = len(num)
            
            from functools import lru_cache
            
            @lru_cache(None)
            def dp(pos: int, tight: bool, current_sum: int) -> int:
                if current_sum > max_sum:
                    return 0
                if pos == n:
                    return 1 if min_sum <= current_sum <= max_sum else 0
                
                limit = int(num[pos]) if tight else 9
                result = 0
                
                for digit in range(limit + 1):
                    new_tight = tight and (digit == limit)
                    result = (result + dp(pos + 1, new_tight, current_sum + digit)) % MOD
                
                return result
            
            return dp(0, True, 0)
        
        # Count from 0 to num2 minus count from 0 to num1-1
        num1_minus_1 = str(int(num1) - 1)
        result = (countUpTo(num2) - countUpTo(num1_minus_1)) % MOD
        return result