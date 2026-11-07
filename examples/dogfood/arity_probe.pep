// arity_probe — T2 follow-up: definition/use arity agreement (flat calls only).
// Pass 1: count "fn " occurrences (reuse v2 idiom). Pass 2: first '(' -> first
// ')' gives the target signature span; last '(' -> its ')' gives the call span.
// Arity = commas+1 (0 when the pair is empty). main returns 0 = agree,
// 1 = no definition, 2 = arity mismatch (covers no-call: args 0 vs params N).
// Single-conditional loops, hoisted cross-chunk calls, trailing return.
// Expected: arity_ok 0, arity_bad 2, arity_nodef 1, arity_nocall 2.

fn is_fn_at(source: SourceBytes, o: Int) -> Int {
  if byte_at(source, o) == 102 && byte_at(source, o + 1) == 110 && byte_at(source, o + 2) == 32 {
    return 1
  } else {
    return 0
  }
}

fn count_fn(source: SourceBytes) -> Int {
  var n = 0
  var o = 0
  var length = byte_length(source)
  while !(length <= o + 2) {
    n = n + is_fn_at(source, o)
    o = o + 1
  }
  return n
}

fn find_open(source: SourceBytes, start: Int) -> Int {
  var o = start
  var found = 0 - 1
  var length = byte_length(source)
  while !(length <= o) {
    if found == 0 - 1 && byte_at(source, o) == 40 {
      found = o
    } else {
    }
    o = o + 1
  }
  return found
}

fn find_last_open(source: SourceBytes) -> Int {
  var o = 0
  var last = 0 - 1
  var length = byte_length(source)
  while !(length <= o) {
    if byte_at(source, o) == 40 {
      last = o
    } else {
    }
    o = o + 1
  }
  return last
}

fn find_close(source: SourceBytes, start: Int) -> Int {
  var o = start
  var found = 0 - 1
  var length = byte_length(source)
  while !(length <= o) {
    if found == 0 - 1 && byte_at(source, o) == 41 {
      found = o
    } else {
    }
    o = o + 1
  }
  return found
}

fn count_commas(source: SourceBytes, lo: Int, hi: Int) -> Int {
  var n = 0
  var o = lo
  while !(hi <= o) {
    if byte_at(source, o) == 44 {
      n = n + 1
    } else {
    }
    o = o + 1
  }
  return n
}

fn main(source: SourceBytes) -> Int {
  var r = 0
  var po = 0
  var pc = 0
  var co = 0
  var cc = 0
  var params = 0
  var args = 0
  if count_fn(source) == 0 {
    r = 1
  } else {
    r = 2
  }
  if r == 2 {
    po = find_open(source, 0)
    pc = find_close(source, po)
    co = find_last_open(source)
    cc = find_close(source, co)
    params = count_commas(source, po, pc)
    args = count_commas(source, co, cc)
    if pc == po + 1 {
      params = 0
    } else {
      params = params + 1
    }
    if cc == co + 1 {
      args = 0
    } else {
      args = args + 1
    }
    if params == args {
      r = 0
    } else {
    }
  } else {
  }
  return r
}
