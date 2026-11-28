import math
from itertools import permutations, product

def solve():
    # Read input
    line1 = input().split()
    N = int(line1[0])
    S = int(line1[1])
    T = int(line1[2])
    
    segments = []
    for i in range(N):
        line = input().split()
        A, B, C, D = int(line[0]), int(line[1]), int(line[2]), int(line[3])
        segments.append(((A, B), (C, D)))
    
    def dist(p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def segment_length(seg):
        return dist(seg[0], seg[1])
    
    min_time = float('inf')
    
    # Try all permutations of segments
    for perm in permutations(range(N)):
        # Try all combinations of starting endpoints (0 = first endpoint, 1 = second endpoint)
        for starts in product([0, 1], repeat=N):
            current_pos = (0, 0)
            total_time = 0.0
            
            for i in range(N):
                seg_idx = perm[i]
                seg = segments[seg_idx]
                
                # Choose starting and ending endpoints based on starts[i]
                if starts[i] == 0:
                    start_ep = seg[0]
                    end_ep = seg[1]
                else:
                    start_ep = seg[1]
                    end_ep = seg[0]
                
                # Time to move from current position to starting endpoint (without laser)
                move_time = dist(current_pos, start_ep) / S
                total_time += move_time
                
                # Time to print the segment (with laser)
                print_time = segment_length(seg) / T
                total_time += print_time
                
                # Update current position to ending endpoint
                current_pos = end_ep
            
            if total_time < min_time:
                min_time = total_time
    
    print(f"{min_time:.20f}")

if __name__ == "__main__":
    solve()