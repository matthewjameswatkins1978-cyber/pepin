fn main(source: SourceBytes) -> Int {
  let s = utf8_slice(source, 0, 3)
  say(s)
  return 0
}
