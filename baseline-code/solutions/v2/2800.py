class Solution:
    def minLength(self, s: str) -> int:
        stack = []
        for char in s:
            stack.append(char)
            # Check if the last two characters form "AB" or "CD"
            while len(stack) >= 2 and (stack[-2] + stack[-1] == "AB" or stack[-2] + stack[-1] == "CD"):
                stack.pop()
                stack.pop()
        return len(stack)