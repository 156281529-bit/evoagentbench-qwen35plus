# YOUR CODE HERE
import sys

def solve() -> None:
    input_data = sys.stdin.read().split()
    idx = 0
    
    T = int(input_data[idx])
    idx += 1
    
    results = []
    
    for _ in range(T):
        N = int(input_data[idx])
        M = int(input_data[idx + 1])
        idx += 2
        
        # Calculate (v - p) for each box, keep only positive values
        positive_diffs = []
        for i in range(N):
            v = int(input_data[idx])
            p = int(input_data[idx + 1])
            idx += 2
            diff = v - p
            if diff > 0:
                positive_diffs.append(diff)
        
        # Sort in ascending order
        positive_diffs.sort()
        
        # Special case: M = 1
        # With only one type, Box can fill all boxes completely
        if M == 1:
            results.append(sum(positive_diffs))
            continue
        
        # If we don't have enough positive values, Box can't guarantee any profit
        if len(positive_diffs) < M - 1:
            results.append(0)
            continue
        
        # Sum of the first (M - 1) smallest positive (v - p) values
        total = sum(positive_diffs[:M - 1])
        
        # If M >= 3, subtract the difference between the (M-1)-th and (M-2)-th values
        if M >= 3:
            total -= (positive_diffs[M - 2] - positive_diffs[M - 3])
        
        results.append(total)
    
    for result in results:
        print(result)

if __name__ == "__main__":
    solve()