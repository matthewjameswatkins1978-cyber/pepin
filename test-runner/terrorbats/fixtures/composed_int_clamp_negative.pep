// Red baseline: the argument-shape edge. int_clamp(-5, 0, 10) exceeds the staged
// parser budget while int_clamp(15, 0, 10) reaches the emitter and is rejected
// as unsupported — the same source, a different argument shape.
fn int_clamp(x: Int, lo: Int, hi: Int) -> Int {
  if x <= lo { return lo } else { if hi <= x { return hi } else { return x } }
}

fn main() -> Int { return int_clamp(-5, 0, 10) }
say(int_text(int_clamp(-5, 0, 10)))
