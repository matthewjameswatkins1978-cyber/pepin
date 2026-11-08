// A3-S1 verification of A2's cross-chunk fix: helper call in a CONDITION.
fn a3_is_one(x: Int) -> Int {
  if x == 1 {
    return 1
  } else {
  }
  return 0
}

fn main(source: SourceBytes) -> Int {
  let b = byte_at(source, 0)
  let hit = a3_is_one(b)
  if hit == 1 {
    say("HIT")
  } else {
  }
  return 0
}