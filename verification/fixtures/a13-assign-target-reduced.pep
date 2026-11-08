fn scan(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var e = i
  var f = 0
  if i + 1 <= n {
    f = 1
  } else {
  }
  while i + 1 <= n {
    if f == 0 {
      if i == 1 {
        e = i
      } else {
        i = n
      }
    } else {
      i = n
    }
  }
  var out = o
  if f == 0 {
    out = e
  } else {
  }
  return out
}

fn main(source: SourceBytes) -> Int {
  return scan(source, 0)
}
