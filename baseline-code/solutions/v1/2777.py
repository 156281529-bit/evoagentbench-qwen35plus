class Solution:
    def distinctDifferenceArray(self, nums: List[int]) -> List[int]:
        n = len(nums)
        diff = []
        
        for i in range(n):
            # Count distinct elements in prefix nums[0, ..., i]
            prefix_distinct = len(set(nums[:i+1]))
            
            # Count distinct elements in suffix nums[i+1, ..., n-1]
            suffix_distinct = len(set(nums[i+1:]))
            
            # Calculate diff[i]
            diff.append(prefix_distinct - suffix_distinct)
        
        return diff