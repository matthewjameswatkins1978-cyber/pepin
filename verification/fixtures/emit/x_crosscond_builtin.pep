// A3-S1: the exact is_ws_at shape - a cross-chunk call whose ARGUMENT is a
// builtin call, used inside a condition.
fn a3_is_one(x: Int) -> Int {
  if x == 1 {
    return 1
  } else {
  }
  return 0
}

fn main(source: SourceBytes) -> Int {
  if a3_is_one(byte_at(source, 0)) == 1 {
    say("HIT")
  } else {
  }
  return 0
}