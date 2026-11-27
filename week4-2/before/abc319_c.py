import itertools

def solve():
    # Read the 3x3 grid
    grid = []
    for _ in range(3):
        row = list(map(int, input().split()))
        grid.append(row)
    
    # Define all 8 lines (3 rows, 3 columns, 2 diagonals)
    lines = [
        [(0, 0), (0, 1), (0, 2)],  # Row 1
        [(1, 0), (1, 1), (1, 2)],  # Row 2
        [(2, 0), (2, 1), (2, 2)],  # Row 3
        [(0, 0), (1, 0), (2, 0)],  # Column 1
        [(0, 1), (1, 1), (2, 1)],  # Column 2
        [(0, 2), (1, 2), (2, 2)],  # Column 3
        [(0, 0), (1, 1), (2, 2)],  # Main diagonal
        [(0, 2), (1, 1), (2, 0)],  # Anti-diagonal
    ]
    
    def check(order):
        """Check if this viewing order causes disappointment"""
        # Map each position to the time it was seen
        pos_to_time = {pos: t for t, pos in enumerate(order)}
        
        for line in lines:
            # Get cells in this line with their viewing times
            cells_with_time = [(pos, pos_to_time[pos]) for pos in line]
            # Sort by viewing time to get the order they were seen
            cells_with_time.sort(key=lambda x: x[1])
            
            # Get values in viewing order
            vals = [grid[pos[0]][pos[1]] for pos, _ in cells_with_time]
            
            # Check disappointment condition: first two same, third different
            if vals[0] == vals[1] and vals[0] != vals[2]:
                return False  # Disappointed
        
        return True  # Not disappointed
    
    # All 9 positions in the grid
    positions = [(i, j) for i in range(3) for j in range(3)]
    
    # Count valid permutations
    count = 0
    total = 0
    
    for perm in itertools.permutations(positions):
        total += 1
        if check(perm):
            count += 1
    
    # Output the probability
    print(count / total)

solve()