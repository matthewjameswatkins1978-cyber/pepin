// Red baseline: int_gcd's transitive closure (int_mod + int_gcd) plus main.
// Measured to abort with PEP_RUNTIME_STEP_LIMIT during the staged parser,
// before the checker or C23 emitter runs (pep/native-differential-v1@920f42c).
fn int_mod(a: Int, b: Int) -> Int {
  var x = a
  while !(x <= b - 1) { x = x - b }
  return x
}

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

fn main() -> Int { return int_gcd(48, 18) }
say(int_text(int_gcd(48, 18)))
