// A3-S1 "no accidental acceptance": a call to a function that does not exist,
// placed in a CONDITION - the exact position A2-S1 added lowering for. If the new
// path bypasses resolution this would emit instead of refusing.
fn main(source: SourceBytes) -> Int {
  if a3_nobody(byte_at(source, 0)) == 1 {
    say("BAD")
  } else {
  }
  return 0
}