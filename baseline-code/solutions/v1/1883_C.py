import sys

def solve():
    input_data = sys.stdin.read().split()
    idx = 0
    t = int(input_data[idx])
    idx += 1
    
    results = []
    
    for _ in range(t):
        n = int(input_data[idx])
        k = int(input_data[idx + 1])
        idx += 2
        a = [int(input_data[idx + i]) for i in range(n)]
        idx += n
        
        if k == 2:
            # Need at least one even number
            has_even = any(x % 2 == 0 for x in a)
            results.append(0 if has_even else 1)
        
        elif k == 3:
            # Need at least one number divisible by 3
            has_div3 = any(x % 3 == 0 for x in a)
            if has_div3:
                results.append(0)
            else:
                min_ops = min((3 - x % 3) % 3 for x in a)
                results.append(min_ops)
        
        elif k == 4:
            # Need product to have at least 2 factors of 2
            def count_factor_2(x):
                count = 0
                while x > 0 and x % 2 == 0:
                    count += 1
                    x //= 2
                return count
            
            total_power_2 = sum(count_factor_2(x) for x in a)
            
            if total_power_2 >= 2:
                results.append(0)
            else:
                # Option 1: Make one number divisible by 4 (gives 2 factors of 2)
                cost_to_div4 = [(4 - x % 4) % 4 for x in a]
                # Option 2: Make two numbers even (each gives 1 factor of 2)
                cost_to_even = [(2 - x % 2) % 2 for x in a]
                
                min_cost = min(cost_to_div4)
                
                # Try making two numbers even
                sorted_even_costs = sorted(cost_to_even)
                if len(sorted_even_costs) >= 2:
                    min_cost = min(min_cost, sorted_even_costs[0] + sorted_even_costs[1])
                
                results.append(min_cost)
        
        elif k == 5:
            # Need at least one number divisible by 5
            has_div5 = any(x % 5 == 0 for x in a)
            if has_div5:
                results.append(0)
            else:
                min_ops = min((5 - x % 5) % 5 for x in a)
                results.append(min_ops)
    
    for result in results:
        print(result)

if __name__ == "__main__":
    solve()