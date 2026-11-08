// A3-S1: transitive cross-chunk chain A -> B -> C, all in separate functions,
// reached from a condition. A2-S1 claims transitive chains work.
fn a3_c(x: Int) -> Int {
  return x + 1
}

fn a3_b(x: Int) -> Int {
  let y = a3_c(x)
  return y
}

fn main(source: SourceBytes) -> Int {
  let n = byte_length(source)
  let r = a3_b(n)
  if r == 5 {
    say("CHAIN")
  } else {
  }
  return 0
}