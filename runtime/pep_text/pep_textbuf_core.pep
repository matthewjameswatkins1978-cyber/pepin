fn grow_step(cap: Int) -> Int {
  let half = 4611686018427387903
  let maxint = 9223372036854775807
  if !(cap <= half) {
    return maxint
  } else {
    return cap + cap
  }
}
fn main() -> Int {
  return if grow_step(4611686018427387904) == 9223372036854775807 { 0 } else { 1 }
}
