// Pepin Core Standard Library Prelude v0.1
// Living Specification: std/prelude.spec.json
// Reversible mathematical, logical, and collection primitives.

type OptionInt = None() | Some(Int)

fn abs(n: Int) -> Int {
    return if n <= 0 { 0 - n } else { n }
}

fn min(a: Int, b: Int) -> Int {
    return if a <= b { a } else { b }
}

fn max(a: Int, b: Int) -> Int {
    return if a <= b { b } else { a }
}

fn clamp(v: Int, lo: Int, hi: Int) -> Int {
    return if v <= lo { lo } else { if hi <= v { hi } else { v } }
}

fn sign(n: Int) -> Int {
    return if n == 0 { 0 } else { if n <= 0 { 0 - 1 } else { 1 } }
}

fn mod(a: Int, b: Int) -> Int {
    return a - ((a / b) * b)
}

fn is_even(n: Int) -> Bool {
    return mod(n, 2) == 0
}

fn is_odd(n: Int) -> Bool {
    return mod(n, 2) != 0
}

fn pow(base: Int, exp: Int) -> Int {
    if exp <= 0 {
        return 1
    } else {
        var res: Int = 1;
        var b: Int = base;
        var e: Int = exp;
        while !(e <= 0) {
            if is_odd(e) {
                res = res * b;
            } else {
                res = res;
            }
            b = b * b;
            e = e / 2;
        }
        return res
    }
}

fn gcd(a: Int, b: Int) -> Int {
    var x: Int = abs(a);
    var y: Int = abs(b);
    while y != 0 {
        let t: Int = y;
        y = mod(x, y);
        x = t;
    }
    return x
}

fn unwrap_or(opt: OptionInt, default_val: Int) -> Int {
    return match opt {
        Some(val) => val
        None() => default_val
    }
}

fn sum(nums: List[Int]) -> Int {
    var total: Int = 0;
    for x in nums {
        total = total + x;
    }
    return total
}

fn list_max(nums: List[Int], default_val: Int) -> Int {
    if length(nums) == 0 {
        return default_val
    } else {
        var best: Int = default_val;
        var first: Bool = true;
        for x in nums {
            if first {
                best = x;
                first = false;
            } else {
                best = max(best, x);
            }
        }
        return best
    }
}

fn list_min(nums: List[Int], default_val: Int) -> Int {
    if length(nums) == 0 {
        return default_val
    } else {
        var best: Int = default_val;
        var first: Bool = true;
        for x in nums {
            if first {
                best = x;
                first = false;
            } else {
                best = min(best, x);
            }
        }
        return best
    }
}

fn count_occurrences(nums: List[Int], target: Int) -> Int {
    var count: Int = 0;
    for x in nums {
        if x == target {
            count = count + 1;
        } else {
            count = count;
        }
    }
    return count
}

fn list_prefix_sum(nums: List[Int], count: Int) -> Int {
    if count <= 0 { return 0 }
    var remaining = count
    var total = 0
    for item in nums {
        total = total + item
        remaining = remaining - 1
        if remaining == 0 { break }
    }
    return total
}

fn list_first_or[T](values: List[T], fallback: T) -> T {
    for value in values {
        return value
    }
    return fallback
}

// Verification runner
let p_abs = abs(0 - 42);
say(int_text(p_abs))
let p_pow = pow(2, 10);
say(int_text(p_pow))
let p_gcd = gcd(48, 18);
say(int_text(p_gcd))
let p_sum = sum([1, 2, 3, 4, 5]);
say(int_text(p_sum))
let p_max = list_max([5, 12, 3, 99, 1], 0);
say(int_text(p_max))
let p_min = list_min([5, 12, 3, 99, 1], 999);
say(int_text(p_min))
let p_opt1 = unwrap_or(Some(77), 0);
say(int_text(p_opt1))
let p_opt2 = unwrap_or(None(), 404);
say(int_text(p_opt2))
let p_cnt = count_occurrences([1, 2, 1, 3, 1, 4], 1);
say(int_text(p_cnt))
