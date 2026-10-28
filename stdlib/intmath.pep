// Pep standard library — integer helpers.
//
// Owner: AGENT 3 (stdlib/intmath.pep). Agent 2 owns stdlib/collections.pep, the
// C23 emitter and its regression files; nothing here touches those.
//
// Written against the operator set this base actually accepts, measured rather
// than assumed: ==  !=  <=  +  -  *  unary -  &&  ||  !  var  let  while
// if/else, function calls including forward references, and integer division.
//
// NOT available on this base — so these helpers avoid them instead of widening
// the language: <   >   >=   %   (each raises PEP_UNEXPECTED_CHARACTER).
// Comparisons are therefore spelled with `<=` plus negation, so `!(a <= b)`
// reads as `a > b`, and remainders are taken by repeated subtraction.
//
// Domains are stated per function. No negative modulo and no overflow claim is
// made: PEP_RUNTIME_OVERFLOW is the interpreter's guard, not a library promise.

// Domain: every Int except the minimum, whose magnitude is not representable
// (negating it raises PEP_RUNTIME_OVERFLOW by design — the guard is not relaxed).
fn int_abs(x: Int) -> Int {
  if x <= -1 { return -x } else { return x }
}

fn int_sign(x: Int) -> Int {
  if x <= -1 { return -1 } else { if x == 0 { return 0 } else { return 1 } }
}

fn int_min(a: Int, b: Int) -> Int {
  if a <= b { return a } else { return b }
}

fn int_max(a: Int, b: Int) -> Int {
  if b <= a { return a } else { return b }
}

// Clamp x into [lo, hi]. Requires lo <= hi; the bounds win when x is outside.
fn int_clamp(x: Int, lo: Int, hi: Int) -> Int {
  if x <= lo { return lo } else { if hi <= x { return hi } else { return x } }
}

// Remainder for 0 <= a and 1 <= b. Subtraction loop, so no `%` is needed.
fn int_mod(a: Int, b: Int) -> Int {
  var x = a
  while !(x <= b - 1) { x = x - b }
  return x
}

// Greatest common divisor for 0 <= a and 0 <= b. gcd(0, n) == n == gcd(n, 0).
fn int_gcd(a: Int, b: Int) -> Int {
  var x = a
  var y = b
  while !(y == 0) {
    let r = int_mod(x, y)
    x = y
    y = r
  }
  return x
}

// Least common multiple for 1 <= a and 1 <= b. Divides before multiplying so a
// large pair overflows later, not sooner.
fn int_lcm(a: Int, b: Int) -> Int {
  let g = int_gcd(a, b)
  return a / g * b
}

// Parity of every Int, including both boundaries. The remainder is taken by
// truncating division (Pep `/` truncates toward zero) so the value is never
// negated: `x - 2 * (x / 2)` is 0 exactly when x is even, and it cannot overflow
// because `2 * (x / 2)` is always representable for the minimum Int too.
fn int_is_even(x: Int) -> Bool {
  let m = x - 2 * (x / 2)
  if m == 0 { return true } else { return false }
}

fn int_is_odd(x: Int) -> Bool {
  if int_is_even(x) { return false } else { return true }
}

// base raised to exp for 0 <= exp. int_pow(b, 0) == 1 for every b.
fn int_pow(base: Int, exp: Int) -> Int {
  var result = 1
  var n = exp
  while 0 <= n - 1 {
    result = result * base
    n = n - 1
  }
  return result
}
