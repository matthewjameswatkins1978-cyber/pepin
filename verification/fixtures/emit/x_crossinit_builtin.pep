// A3-S1: cross-chunk call in a VAR INITIALISER whose argument is a builtin call.
fn a3_double(x: Int) -> Int {
  return x + x
}

fn main(source: SourceBytes) -> Int {
  let d = a3_double(byte_length(source))
  say(int_text(d))
  return 0
}