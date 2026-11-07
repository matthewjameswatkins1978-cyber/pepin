fn is_ws(b: Int) -> Bool {
  if b == 32 { return true } else { }
  if b == 10 { return true } else { }
  if b == 9 { return true } else { }
  return false
}

fn is_letter(b: Int) -> Bool {
  if 65 <= b { if b <= 90 { return true } else { } } else { }
  if 97 <= b { if b <= 122 { return true } else { } } else { }
  if b == 95 { return true } else { }
  return false
}

fn is_digit(b: Int) -> Bool {
  if 48 <= b { if b <= 57 { return true } else { } } else { }
  return false
}

fn classify(b: Int) -> Int {
  if is_ws(b) {
    return 0
  } else {
    if is_letter(b) {
      return 1
    } else {
      if is_digit(b) { return 2 } else { return 3 }
    }
  }
  return 3
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
