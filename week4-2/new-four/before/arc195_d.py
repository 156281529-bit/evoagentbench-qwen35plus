import sys
from collections import defaultdict

def solve():
    input = sys.stdin.read
    data = input().split()
    
    idx = 0
    T = int(data[idx])
    idx += 1
    
    results = []
    
    for _ in range(T):
        N = int(data[idx])
        idx += 1
        A = [int(data[idx + i]) for i in range(N)]
        idx += N
        
        # Count the number of runs of each value
        run_counts = defaultdict(int)
        if N > 0:
            current_run_value = A[0]
            for i in range(1, N):
                if A[i] != current_run_value:
                    run_counts[current_run_value] += 1
                    current_run_value = A[i]
            run_counts[current_run_value] += 1
        
        num_runs = sum(run_counts.values())
        
        # Find the maximum floor((number of runs of value v) / 2)
        max_savings = 0
        for value in run_counts:
            savings = run_counts[value] // 2
            if savings > max_savings:
                max_savings = savings
        
        # Answer
        answer = num_runs - max_savings
        results.append(str(answer))
    
    print('\n'.join(results))

if __name__ == "__main__":
    solve()