// Control fixture: valid, natively supported, and a known-good oracle target.
// Used by the deliberately failing control Bat.
fn int_abs(x: Int) -> Int {
  if x <= -1 { return -x } else { return x }
}

fn main() -> Int { return int_abs(-7) }
say(int_text(int_abs(-7)))
