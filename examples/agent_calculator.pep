// Pepin Exemplary Module: Agent Calculator
// Linked to Living Program Specification: agent_calculator.spec.json

fn factorial(n: Int) -> Int {
  if n <= 1 {
    return 1
  } else {
    return n * factorial(n - 1)
  }
}

fn power(base: Int, exp: Int) -> Int {
  if exp <= 0 {
    return 1
  } else {
    return base * power(base, exp - 1)
  }
}

fn clamp(val: Int, min_val: Int, max_val: Int) -> Int {
  if val <= min_val {
    return min_val
  } else {
    if max_val <= val {
      return max_val
    } else {
      return val
    }
  }
}

fn calculate_clamped_factorial(n: Int, limit: Int) -> Int {
  let raw = factorial(n)
  return clamp(raw, 1, limit)
}

fn main() -> Int {
  let res = calculate_clamped_factorial(5, 100)
  return res
}
