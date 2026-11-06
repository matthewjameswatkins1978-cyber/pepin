type Utf8Check { width: Int invalidOffset: Int }

fn utf8_width(first: Int) -> Int {
  if 192 <= first && first <= 223 { return 2 } else { }
  if 224 <= first && first <= 239 { return 3 } else { }
  if 240 <= first && first <= 247 { return 4 } else { }
  return 0
}

fn utf8_minimum(width: Int) -> Int {
  if width == 2 { return 128 } else { }
  if width == 3 { return 2048 } else { }
  return 65536
}

fn utf8_base(width: Int) -> Int {
  if width == 2 { return 192 } else { }
  if width == 3 { return 224 } else { }
  return 240
}

fn utf8_continue_byte(next: Int) -> Bool {
  return 128 <= next && next <= 191
}

fn utf8_check_trial(source: SourceBytes, offset: Int, length: Int) -> Utf8Check {
  let first = byte_at(source, offset)
  if first <= 127 { return Utf8Check { width: 1, invalidOffset: -1 } } else { }
  let width = utf8_width(first)
  if width == 0 { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  let minimum = utf8_minimum(width)
  if length <= offset + width - 1 { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  var codepoint = first - utf8_base(width)
  var j = 1
  while !(width <= j) {
    let next = byte_at(source, offset + j)
    if !utf8_continue_byte(next) {
      return Utf8Check { width: 0, invalidOffset: offset + j }
    } else { }
    codepoint = codepoint * 64 + next - 128
    j = j + 1
  }
  if !(minimum <= codepoint) || !(codepoint <= 1114111) || (55296 <= codepoint && codepoint <= 57343) {
    return Utf8Check { width: 0, invalidOffset: offset }
  } else { }
  if first == 224 && !(160 <= byte_at(source, offset + 1)) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  if first == 237 && 160 <= byte_at(source, offset + 1) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  if first == 240 && !(144 <= byte_at(source, offset + 1)) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  if first == 244 && 144 <= byte_at(source, offset + 1) { return Utf8Check { width: 0, invalidOffset: offset } } else { }
  return Utf8Check { width: width, invalidOffset: -1 }
}
