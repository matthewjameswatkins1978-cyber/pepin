# Agent-4 find policy model: byte-substring search over List[Int],
# mirroring pep_text_find in pep_find.c. Bytes are Ints 0-255; Pep has
# no byte type and no indexing, so access walks the list. Written for
# the CLI interpreter (1M-step budget) and marked UNTESTED: the hold
# forbids executing even the OCaml seed here. Verify post-hold with
# `check` (must be valid) and `run` (must print the expected values).
# Pep has no `<` operator, only `<=`, hence the `!(b <= a)` form.

fn list_byte_at(values: List[Int], index: Int) -> Int {
  var position = 0
  var result = -1
  for value in values {
    if position == index && result == -1 { result = value } else { }
    position = position + 1
  }
  return result
}

fn match_at(hay: List[Int], start: Int, ndl: List[Int]) -> Bool {
  var ok = true
  var j = 0
  while ok && !(length(ndl) <= j) {
    if list_byte_at(hay, start + j) == list_byte_at(ndl, j) { j = j + 1 } else { ok = false }
  }
  return ok
}

fn find_first(hay: List[Int], ndl: List[Int]) -> Int {
  let hlen = length(hay)
  let nlen = length(ndl)
  if nlen == 0 { return 0 } else { }
  var best = hlen
  var i = 0
  while i <= hlen - nlen {
    if match_at(hay, i, ndl) { best = i; i = hlen } else { i = i + 1 }
  }
  return best
}

say(int_text(find_first([97, 98, 99], [98, 99])))
say(int_text(find_first([97, 98, 99], [])))
say(int_text(find_first([97, 98, 99], [99, 100])))
say(int_text(find_first([195, 169], [169])))
say(int_text(find_first([], [65])))
say(int_text(find_first([], [])))
say(int_text(find_first([65], [65, 66])))
say(int_text(find_first([0, 65], [0])))
