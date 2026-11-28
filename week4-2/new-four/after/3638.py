from collections import Counter


class Solution:
    def makeStringGood(self, s: str) -> int:
        counts = Counter(s)
        freq = [counts[chr(ord("a") + i)] for i in range(26)]
        best = len(s)
        for target in range(1, max(freq) + 1):
            # Each letter ends at either zero or target. A surplus at i can
            # replace an insertion at i+1. Longer moves cost at least as
            # much as deleting and reinserting.
            previous_goals = (0, target)
            costs = [freq[0], abs(freq[0] - target)]
            for left, right in zip(freq, freq[1:]):
                next_costs = []
                for goal in previous_goals:
                    missing = max(0, goal - right)
                    options = (cost - min(max(0, left - old_goal), missing)
                               for old_goal, cost in zip(previous_goals, costs))
                    next_costs.append(abs(right - goal) + min(options))
                costs = next_costs
            best = min(best, *costs)
        return best
