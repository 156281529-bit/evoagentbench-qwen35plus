import sys

def solve() -> None:
    input_data = sys.stdin.read().split()
    idx = 0
    
    T = int(input_data[idx])
    idx += 1
    
    results = []
    
    for _ in range(T):
        N = int(input_data[idx])
        K = int(input_data[idx + 1])
        idx += 2
        
        cakes = []
        for i in range(N):
            X = int(input_data[idx])
            Y = int(input_data[idx + 1])
            Z = int(input_data[idx + 2])
            idx += 3
            cakes.append((X, Y, Z))
        
        # Pre-sort options by value descending
        options = []
        for i, (X, Y, Z) in enumerate(cakes):
            options.append((X, 0, i))
            options.append((Y, 1, i))
            options.append((Z, 2, i))
        options.sort(reverse=True)
        
        best_total = 0
        
        # Enumerate over all possible splits (k1, k2, k3) where k1 + k2 + k3 = K
        for k1 in range(K + 1):
            for k2 in range(K + 1 - k1):
                k3 = K - k1 - k2
                
                n1 = 2 * k1
                n2 = 2 * k2
                n3 = 2 * k3
                total_cakes = n1 + n2 + n3
                
                # Greedy assignment using pre-sorted options
                assigned_cakes = set()
                dim_count = [0, 0, 0]
                dim_limit = [n1, n2, n3]
                total = 0
                
                for value, dim, cake_idx in options:
                    if cake_idx in assigned_cakes:
                        continue
                    if dim_count[dim] >= dim_limit[dim]:
                        continue
                    assigned_cakes.add(cake_idx)
                    dim_count[dim] += 1
                    total += value
                    
                    if len(assigned_cakes) == total_cakes:
                        break
                
                if len(assigned_cakes) == total_cakes:
                    best_total = max(best_total, total)
        
        results.append(best_total)
    
    for r in results:
        print(r)

if __name__ == "__main__":
    solve()