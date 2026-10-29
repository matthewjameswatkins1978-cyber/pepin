fn utf8_cont(byte: Int) -> Int {
  if !(byte <= 127) {
    return if byte <= 191 { 1 } else { 0 }
  } else {
    return 0
  }
}
fn main() -> Int {
  return if utf8_cont(128) == 1 { if utf8_cont(65) == 0 { 0 } else { 1 } } else { 1 }
}
