import sys

def solve():
    input_data = sys.stdin.read().split()
    idx = 0
    T = int(input_data[idx])
    idx += 1
    
    results = []
    for _ in range(T):
        K = int(input_data[idx])
        S_x = int(input_data[idx+1])
        S_y = int(input_data[idx+2])
        T_x = int(input_data[idx+3])
        T_y = int(input_data[idx+4])
        idx += 5
        
        # Find start tile
        # For H tile: i = floor((S_x + 0.5) / K), j*K + k = S_y
        i1_h = (2 * S_x + 1) // (2 * K)
        j1_h = S_y // K
        k1_h = S_y % K
        
        # Check if H tile is valid (same parity)
        if i1_h % 2 == j1_h % 2:
            tile1_type = 'H'
            i1, j1, k1 = i1_h, j1_h, k1_h
        else:
            # Must be V tile: j = floor((S_y + 0.5) / K), i*K + k = S_x
            j1_v = (2 * S_y + 1) // (2 * K)
            i1_v = S_x // K
            k1_v = S_x % K
            tile1_type = 'V'
            i1, j1, k1 = i1_v, j1_v, k1_v
        
        # Find end tile
        i2_h = (2 * T_x + 1) // (2 * K)
        j2_h = T_y // K
        k2_h = T_y % K
        
        if i2_h % 2 == j2_h % 2:
            tile2_type = 'H'
            i2, j2, k2 = i2_h, j2_h, k2_h
        else:
            j2_v = (2 * T_y + 1) // (2 * K)
            i2_v = T_x // K
            k2_v = T_x % K
            tile2_type = 'V'
            i2, j2, k2 = i2_v, j2_v, k2_v
        
        # Compute distance
        di = abs(i2 - i1)
        dj = abs(j2 - j1)
        dk = abs(k2 - k1)
        
        if tile1_type == tile2_type:
            # Same type: sum of two largest
            dist = di + dj + dk - min(di, dj, dk)
        else:
            # Different types: sum of all three
            dist = di + dj + dk
        
        results.append(str(dist))
    
    print('\n'.join(results))

if __name__ == '__main__':
    solve()