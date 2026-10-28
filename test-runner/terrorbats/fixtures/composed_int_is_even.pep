// Red baseline: int_is_even (rewritten as truncating-division parity) plus main.
// Single library function; measured to abort in the staged parser.
fn int_is_even(x: Int) -> Bool {
  let m = x - 2 * (x / 2)
  if m == 0 { return true } else { return false }
}

fn main() -> Int { if int_is_even(4) { return 1 } else { return 0 } }
say(if int_is_even(4) { "true" } else { "false" })
