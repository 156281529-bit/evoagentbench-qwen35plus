class Solution:
    def makeStringGood(self, s: str) -> int:
        from collections import Counter
        
        n = len(s)
        count = Counter(s)
        
        min_ops = float('inf')
        
        for f in range(1, n + 1):
            for k in range(1, 27):
                # Calculate contribution of each character (capped at f)
                contribs = []
                for c in range(26):
                    char = chr(ord('a') + c)
                    contribs.append((min(count.get(char, 0), f), c))
                
                # Sort descending by contribution
                contribs.sort(reverse=True)
                
                # Top k characters
                selected = set(c for _, c in contribs[:k])
                sum_contrib = sum(contrib for contrib, c in contribs[:k])
                
                # Base cost = deletions + insertions
                base_cost = n + k * f - 2 * sum_contrib
                
                # Calculate excess and deficit for selected characters only
                excess = [0] * 26
                deficit = [0] * 26
                for c in range(26):
                    if c in selected:
                        char = chr(ord('a') + c)
                        cnt = count.get(char, 0)
                        if cnt > f:
                            excess[c] = cnt - f
                        elif cnt < f:
                            deficit[c] = f - cnt
                
                # Calculate max changes (only between adjacent selected chars)
                # Change can convert excess at position c to help deficit at c+1
                changes = 0
                carry = 0
                for c in range(26):
                    if c in selected:
                        available = carry + excess[c]
                        can_use = min(available, deficit[c])
                        changes += can_use
                        carry = available - can_use
                    else:
                        carry = 0  # Reset carry when encountering non-selected char
                
                total_cost = base_cost - changes
                min_ops = min(min_ops, total_cost)
        
        return min_ops