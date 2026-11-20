import sys

def solve():
    input_data = sys.stdin.read().split()
    idx = 0
    t = int(input_data[idx])
    idx += 1
    
    results = []
    
    for _ in range(t):
        n, k = int(input_data[idx]), int(input_data[idx+1])
        idx += 2
        a = [int(input_data[idx+i]) for i in range(n)]
        idx += n
        
        if k == 2:
            # Need at least one even number
            has_even = any(x % 2 == 0 for x in a)
            results.append(0 if has_even else 1)
        
        elif k == 3:
            # Need at least one number divisible by 3
            min_ops = min((3 - x % 3) % 3 for x in a)
            results.append(min_ops)
        
        elif k == 4:
            # Need either one number divisible by 4, or two even numbers
            has_div4 = any(x % 4 == 0 for x in a)
            if has_div4:
                results.append(0)
            else:
                # Count even numbers
                evens = [x for x in a if x % 2 == 0]
                if len(evens) >= 2:
                    results.append(0)
                else:
                    # Option 1: Make one number divisible by 4
                    min_to_div4 = min((4 - x % 4) % 4 for x in a)
                    # Option 2: Make two numbers even
                    costs_to_even = sorted([(2 - x % 2) % 2 for x in a])
                    min_two_even = costs_to_even[0] + costs_to_even[1]
                    results.append(min(min_to_div4, min_two_even))
        
        elif k == 5:
            # Need at least one number divisible by 5
            min_ops = min((5 - x % 5) % 5 for x in a)
            results.append(min_ops)
    
    for result in results:
        print(result)

solve()