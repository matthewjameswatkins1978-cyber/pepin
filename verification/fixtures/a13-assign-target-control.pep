fn helper(b: Int) -> Int {
  var r = 0
  if b == 65 {
    r = 1
  } else {
  }
  return r
}

fn scan(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var f = 0
  if i + 1 <= n {
    f = 1
  } else {
  }
  var e = i
  while i + 1 <= n {
    if f == 1 {
      if helper(byte_at(source, i)) == 1 {
        i = i + 1
      } else {
        f = 2
        i = n
      }
    } else {
      i = n
    }
  }
  var out = o
  if f == 1 {
    out = e
  } else {
  }
  return out
}

fn main(source: SourceBytes) -> Int {
  return scan(source, 0)
}