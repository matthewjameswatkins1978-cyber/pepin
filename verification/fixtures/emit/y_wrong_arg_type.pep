// A3-S1 "no accidental acceptance": wrong ARGUMENT TYPE in a condition position.
fn a3_is_one(x: Int) -> Int {
  return x
}

fn main(source: SourceBytes) -> Int {
  if a3_is_one("text") == 1 {
    say("BAD")
  } else {
  }
  return 0
}