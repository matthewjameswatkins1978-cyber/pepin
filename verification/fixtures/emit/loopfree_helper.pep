fn classify(b: Int) -> Int {
  if b == 32 {
    return 1
  } else {
    return 2
  }
}

fn main(source: SourceBytes) -> Int {
  var n = 0
  var o = 0
  while !(byte_length(source) <= o) {
    n = n + classify(byte_at(source, o))
    o = o + 1
  }
  return n
}
