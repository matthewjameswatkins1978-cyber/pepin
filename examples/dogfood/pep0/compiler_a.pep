// compiler_a — Pep-0 tiny compiler A, canonical source (A4 lane, slice 1).
// Subset S0: exactly `fn main() -> Int { return DECIMAL }`, DECIMAL 1-18
// ASCII digits. Tokens separated by space/tab/LF/CR: required after `fn`
// and after `return`; optional around all other joints; `->` contiguous.
// Glued forms (`fnmain`, `return42`) are rejected, not misread.
// Input: granted file bytes via main(source). Output: C23 fragments via
// say, one per line (newlines are insignificant in C; punctuation is
// emitted via int_text so literals stay alphanumeric+space).
// Exit codes: 0 ok, 1 bad shape, 2 bad literal, 3 trailing junk,
// 4 literal too long. Truncated inputs fail closed, never wrong C.

fn is_ws(b: Int) -> Int {
  var r = 0
  if b == 32 || b == 9 || b == 10 || b == 13 {
    r = 1
  } else {
  }
  return r
}

fn is_digit(b: Int) -> Int {
  var r = 0
  if 48 <= b && b <= 57 {
    r = 1
  } else {
  }
  return r
}

fn is_ws_at(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 1 <= byte_length(source) && is_ws(byte_at(source, o)) == 1 {
    r = 1
  } else {
  }
  return r
}

fn is_fn2(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 2 <= byte_length(source) && byte_at(source, o) == 102 && byte_at(source, o + 1) == 110 {
    r = 1
  } else {
  }
  return r
}

fn is_main4(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 4 <= byte_length(source) && byte_at(source, o) == 109 && byte_at(source, o + 1) == 97 && byte_at(source, o + 2) == 105 && byte_at(source, o + 3) == 110 {
    r = 1
  } else {
  }
  return r
}

fn is_int3(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 3 <= byte_length(source) && byte_at(source, o) == 73 && byte_at(source, o + 1) == 110 && byte_at(source, o + 2) == 116 {
    r = 1
  } else {
  }
  return r
}

fn is_ret3(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 3 <= byte_length(source) && byte_at(source, o) == 114 && byte_at(source, o + 1) == 101 && byte_at(source, o + 2) == 116 {
    r = 1
  } else {
  }
  return r
}

fn is_urn3(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 3 <= byte_length(source) && byte_at(source, o) == 117 && byte_at(source, o + 1) == 114 && byte_at(source, o + 2) == 110 {
    r = 1
  } else {
  }
  return r
}

fn expect_byte(source: SourceBytes, o: Int, want: Int) -> Int {
  var r = 0
  if o + 1 <= byte_length(source) && byte_at(source, o) == want {
    r = 1
  } else {
  }
  return r
}

fn skip_ws(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var pos = o
  var f = 0
  while i + 1 <= n {
    if is_ws(byte_at(source, i)) == 1 {
      i = i + 1
    } else {
      pos = i
      f = 1
      i = n
    }
  }
  var out = n
  if f == 1 {
    out = pos
  } else {
  }
  return out
}

fn scan_digits(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var pos = o
  var f = 0
  while i + 1 <= n {
    if is_digit(byte_at(source, i)) == 1 {
      i = i + 1
    } else {
      pos = i
      f = 1
      i = n
    }
  }
  var out = n
  if f == 1 {
    out = pos
  } else {
  }
  return out
}

fn parse_value(source: SourceBytes, o: Int, end: Int) -> Int {
  var v = 0
  var i = o
  while i + 1 <= end {
    v = v * 10 + (byte_at(source, i) - 48)
    i = i + 1
  }
  return v
}

fn find_fn(source: SourceBytes) -> Int {
  var err = 0
  var o = skip_ws(source, 0)
  if is_fn2(source, o) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 2
  } else {
  }
  if err == 0 && is_ws_at(source, o) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 && is_main4(source, o) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 4
  } else {
  }
  var out = 0 - 1
  if err == 0 {
    out = o
  } else {
  }
  return out
}

fn find_parens(source: SourceBytes, p: Int, err_in: Int) -> Int {
  var out = 0 - 1
  var o = p
  var err = err_in
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 && expect_byte(source, o, 40) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 1
  } else {
  }
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 && expect_byte(source, o, 41) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 1
  } else {
  }
  if err == 0 {
    out = o
  } else {
  }
  return out
}

fn find_brace(source: SourceBytes, p: Int, err_in: Int) -> Int {
  var out = 0 - 1
  var o = p
  var err = err_in
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 && expect_byte(source, o, 45) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 1
  } else {
  }
  if err == 0 && expect_byte(source, o, 62) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 1
  } else {
  }
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 && is_int3(source, o) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 3
  } else {
  }
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 && expect_byte(source, o, 123) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 1
  } else {
  }
  if err == 0 {
    out = o
  } else {
  }
  return out
}

fn find_ds(source: SourceBytes, h: Int, err_in: Int) -> Int {
  var out = 0 - 1
  var o = h
  var err = err_in
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 && is_ret3(source, o) == 0 {
    err = 1
  } else {
  }
  if err == 0 && is_urn3(source, o + 3) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    o = o + 6
  } else {
  }
  if err == 0 && is_ws_at(source, o) == 0 {
    err = 2
  } else {
  }
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  var ds = 0 - 1
  var e = 0 - 1
  if err == 0 {
    ds = o
    e = scan_digits(source, o)
  } else {
  }
  if err == 0 && e == ds {
    err = 2
  } else {
  }
  if err == 0 {
    out = ds
  } else {
  }
  if err == 2 {
    out = 0 - 2
  } else {
  }
  return out
}

fn check_tail(source: SourceBytes, e: Int, err_in: Int) -> Int {
  var r = err_in
  var o = e
  if err_in == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err_in == 0 && expect_byte(source, o, 125) == 0 {
    r = 1
  } else {
  }
  if err_in == 0 {
    o = o + 1
  } else {
  }
  if err_in == 0 {
    o = skip_ws(source, o)
  } else {
  }
  var rest = byte_length(source) - o
  if err_in == 0 && 1 <= rest {
    r = 3
  } else {
  }
  return r
}

fn main(source: SourceBytes) -> Int {
  var err = 0
  var neg1 = 0 - 1
  var neg2 = 0 - 2
  var h1 = find_fn(source)
  if h1 == neg1 {
    err = 1
  } else {
  }
  var h2 = find_parens(source, h1, err)
  if err == 0 && h2 == neg1 {
    err = 1
  } else {
  }
  var h3 = find_brace(source, h2, err)
  if err == 0 && h3 == neg1 {
    err = 1
  } else {
  }
  var ds = find_ds(source, h3, err)
  if err == 0 && ds == neg1 {
    err = 1
  } else {
  }
  if err == 0 && ds == neg2 {
    err = 2
  } else {
  }
  var e = 0
  if err == 0 {
    e = scan_digits(source, ds)
  } else {
  }
  if err == 0 && 19 <= e - ds {
    err = 4
  } else {
  }
  var v = 0
  if err == 0 {
    v = parse_value(source, ds, e)
  } else {
  }
  var tail = check_tail(source, e, err)
  if err == 0 {
    err = tail
  } else {
  }
  if err == 0 {
    say("int main")
    say(int_text(40))
    say("void")
    say(int_text(41))
    say(int_text(123))
    say("return")
    say(int_text(v))
    say(int_text(59))
    say(int_text(125))
  } else {
  }
  if err == 1 {
    say("ERR shape")
  } else {
  }
  if err == 2 {
    say("ERR literal")
  } else {
  }
  if err == 3 {
    say("ERR junk")
  } else {
  }
  if err == 4 {
    say("ERR longlit")
  } else {
  }
  return err
}
