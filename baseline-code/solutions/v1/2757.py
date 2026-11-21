class Solution:
    def count(self, num1: str, num2: str, min_sum: int, max_sum: int) -> int:
        MOD = 10**9 + 7
        
        def countUpTo(num: str) -> int:
            """Count numbers from 0 to num (inclusive) with digit sum in [min_sum, max_sum]"""
            n = len(num)
            from functools import lru_cache
            
            @lru_cache(None)
            def dp(pos: int, curr_sum: int, tight: bool) -> int:
                # If current sum already exceeds max_sum, prune
                if curr_sum > max_sum:
                    return 0
                # Base case: we've placed all digits
                if pos == n:
                    return 1 if min_sum <= curr_sum <= max_sum else 0
                
                # Determine the upper bound for current digit
                limit = int(num[pos]) if tight else 9
                result = 0
                for d in range(limit + 1):
                    new_tight = tight and (d == limit)
                    result = (result + dp(pos + 1, curr_sum + d, new_tight)) % MOD
                
                return result
            
            return dp(0, 0, True)
        
        # Count from 0 to num2 minus count from 0 to num1-1
        num1_minus_1 = str(int(num1) - 1)
        
        result = (countUpTo(num2) - countUpTo(num1_minus_1)) % MOD
        return result