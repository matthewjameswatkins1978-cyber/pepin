// compiler_a -- Pep-0 tiny compiler A, canonical source (A4 lane, slice 1).
// Subset S0: exactly `fn main() -> Int { return DECIMAL }`, DECIMAL 1-18
// ASCII digits. Tokens separated by space/tab/LF/CR: required after `fn`
// and after `return`; optional around all other joints; `->` contiguous.
// Glued forms (`fnmain`, `return42`) are rejected, not misread.
// Input: granted file bytes via main(source). Output: C23 fragments via
// say, one per line (newlines are insignificant in C; punctuation via
// say-string literals, int_text only for the parsed value).
// Exit codes: 0 ok (empty input also exits 0 silent, mirroring seed-valid),
// 1 bad shape, 2 bad literal, 3 trailing junk, 4 literal too long,
// 5 unsupported (seed-valid but out-of-subset, e.g. `-> Str`).
// Truncated inputs fail closed, never wrong C.

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

fn is_str3(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 3 <= byte_length(source) && byte_at(source, o) == 83 && byte_at(source, o + 1) == 116 && byte_at(source, o + 2) == 114 {
    r = 1
  } else {
  }
  return r
}

fn is_bool4(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 4 <= byte_length(source) && byte_at(source, o) == 66 && byte_at(source, o + 1) == 111 && byte_at(source, o + 2) == 111 && byte_at(source, o + 3) == 108 {
    r = 1
  } else {
  }
  return r
}

fn is_unit4(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 4 <= byte_length(source) && byte_at(source, o) == 85 && byte_at(source, o + 1) == 110 && byte_at(source, o + 2) == 105 && byte_at(source, o + 3) == 116 {
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
  var e0len = byte_length(source) - o
  if e0len <= 0 {
    err = 6
  } else {
  }
  if err == 0 && is_fn2(source, o) == 0 {
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
  if err == 6 {
    out = 0 - 6
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
  var e0 = err_in
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
  if e0 == 0 && err == 1 && is_str3(source, o) == 1 {
    err = 5
  } else {
  }
  if e0 == 0 && err == 1 && is_bool4(source, o) == 1 {
    err = 5
  } else {
  }
  if e0 == 0 && err == 1 && is_unit4(source, o) == 1 {
    err = 5
  } else {
  }
  if e0 == 0 && err == 5 && is_str3(source, o) == 1 && is_ws_at(source, o + 3) == 0 && expect_byte(source, o + 3, 123) == 0 {
    err = 1
  } else {
  }
  if e0 == 0 && err == 5 && is_bool4(source, o) == 1 && is_ws_at(source, o + 4) == 0 && expect_byte(source, o + 4, 123) == 0 {
    err = 1
  } else {
  }
  if e0 == 0 && err == 5 && is_unit4(source, o) == 1 && is_ws_at(source, o + 4) == 0 && expect_byte(source, o + 4, 123) == 0 {
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
  if err == 5 {
    out = 0 - 5
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

fn is_var3(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 3 <= byte_length(source) && byte_at(source, o) == 118 && byte_at(source, o + 1) == 97 && byte_at(source, o + 2) == 114 {
    r = 1
  } else {
  }
  return r
}

fn is_let3(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 3 <= byte_length(source) && byte_at(source, o) == 108 && byte_at(source, o + 1) == 101 && byte_at(source, o + 2) == 116 {
    r = 1
  } else {
  }
  return r
}

fn is_true4(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 4 <= byte_length(source) && byte_at(source, o) == 116 && byte_at(source, o + 1) == 114 && byte_at(source, o + 2) == 117 && byte_at(source, o + 3) == 101 {
    r = 1
  } else {
  }
  return r
}

fn is_fals4(source: SourceBytes, o: Int) -> Int {
  var r = 0
  if o + 4 <= byte_length(source) && byte_at(source, o) == 102 && byte_at(source, o + 1) == 97 && byte_at(source, o + 2) == 108 && byte_at(source, o + 3) == 115 {
    r = 1
  } else {
  }
  return r
}

fn is_namech(b: Int) -> Int {
  var r = 0
  if 48 <= b && b <= 57 {
    r = 1
  } else {
  }
  if r == 0 && 65 <= b && b <= 90 {
    r = 1
  } else {
  }
  if r == 0 && 97 <= b && b <= 122 {
    r = 1
  } else {
  }
  if r == 0 && b == 95 {
    r = 1
  } else {
  }
  return r
}

fn scan_name(source: SourceBytes, o: Int) -> Int {
  var i = o
  var n = byte_length(source)
  var f = 0
  if i + 1 <= n {
    if 65 <= byte_at(source, i) && byte_at(source, i) <= 90 {
      f = 1
    } else {
    }
  } else {
  }
  if f == 0 {
    if i + 1 <= n {
      if 97 <= byte_at(source, i) && byte_at(source, i) <= 122 {
        f = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if f == 0 {
    if i + 1 <= n {
      if byte_at(source, i) == 95 {
        f = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if f == 1 {
    i = i + 1
  } else {
  }
  var e: Int = i
  while i + 1 <= n {
    if f == 1 {
      if is_namech(byte_at(source, i)) == 1 {
        i = i + 1
        e = i
      } else {
        f = 2
        i = n
      }
    } else {
      i = n
    }
  }
  var out = o
  if f == 1 || f == 2 {
    out = e
  } else {
  }
  var olen = out - o
  if olen == 1 {
    if byte_at(source, o) == 95 {
      out = o
    } else {
    }
  } else {
  }
  return out
}

fn scan_string(source: SourceBytes, o: Int) -> Int {
  var out = o
  var n = byte_length(source)
  var err = 0
  if expect_byte(source, o, 34) == 0 {
    err = 1
  } else {
  }
  var q = o
  if err == 0 {
    q = o + 1
  } else {
  }
  var closed = 0
  var scanning = 0
  if err == 0 {
    scanning = 1
  } else {
  }
  var endq = o
  while q + 1 <= n {
    if scanning == 1 {
      if byte_at(source, q) == 34 {
        closed = 1
        scanning = 0
        endq = q + 1
        q = n
      } else {
        q = q + 1
      }
    } else {
      q = n
    }
  }
  if closed == 1 {
    out = endq
  } else {
  }
  return out
}

fn scan_value(source: SourceBytes, o: Int) -> Int {
  var out = o
  var n = byte_length(source)
  var err = 0
  var p = o
  var neg = 0
  if expect_byte(source, p, 45) == 1 {
    neg = 1
  } else {
  }
  if neg == 1 {
    p = p + 1
  } else {
  }
  if neg == 1 {
    p = skip_ws(source, p)
  } else {
  }
  var d1: Int = p
  if err == 0 {
    d1 = scan_digits(source, p)
  } else {
  }
  if d1 == p {
    err = 1
  } else {
  }
  if err == 0 {
    if 19 <= d1 - p {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    p = d1
  } else {
  }
  var more = 0
  if err == 0 {
    more = 1
  } else {
  }
  var q: Int = p
  var hasop = 0
  var d2: Int = 0
  while q + 1 <= n {
    if more == 1 {
      q = skip_ws(source, q)
      hasop = 0
      if q + 1 <= n {
        if byte_at(source, q) == 43 || byte_at(source, q) == 42 || byte_at(source, q) == 45 || byte_at(source, q) == 47 {
          hasop = 1
        } else {
        }
      } else {
      }
      if hasop == 1 {
        q = q + 1
      } else {
      }
      if hasop == 1 {
        q = skip_ws(source, q)
      } else {
      }
      d2 = q
      if hasop == 1 {
        d2 = scan_digits(source, q)
      } else {
      }
      if hasop == 1 {
        if d2 == q {
          err = 1
        } else {
        }
      } else {
      }
      if hasop == 1 {
        if err == 0 {
          if 19 <= d2 - q {
            err = 1
          } else {
          }
        } else {
        }
      } else {
      }
      if hasop == 1 {
        if err == 0 {
          p = d2
          q = d2
        } else {
        }
      } else {
      }
      if hasop == 0 {
        more = 0
        q = n
      } else {
      }
      if err == 1 {
        more = 0
        q = n
      } else {
      }
    } else {
      q = n
    }
  }
  if err == 0 {
    out = p
  } else {
  }
  return out
}

fn bytes_eq(source: SourceBytes, i: Int, j: Int) -> Int {
  var a = byte_at(source, i)
  var b = byte_at(source, j)
  var r = 0
  if a == b {
    r = 1
  } else {
  }
  return r
}

fn names_equal(source: SourceBytes, a1: Int, a2: Int, b1: Int, b2: Int) -> Int {
  var r = 0
  var same = 0
  if a2 - a1 == b2 - b1 {
    same = 1
  } else {
  }
  var k = 0
  var lim = a2 - a1
  while k + 1 <= lim {
    if same == 1 {
      if bytes_eq(source, a1 + k, b1 + k) == 1 {
        k = k + 1
      } else {
        same = 0
        k = lim
      }
    } else {
      k = lim
    }
  }
  if same == 1 {
    r = 1
  } else {
  }
  return r
}

fn match_tail(source: SourceBytes, o: Int, fs: Int, fe: Int) -> Int {
  var r = 0
  var n = byte_length(source)
  var err = 0
  var p = skip_ws(source, o)
  if expect_byte(source, p, 125) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    p = p + 1
  } else {
  }
  if err == 0 {
    p = skip_ws(source, p)
  } else {
  }
  if err == 0 {
    if p == n {
      r = 1
    } else {
    }
  } else {
  }
  var q: Int = p
  var hasfn = 0
  if err == 0 {
    if r == 0 {
      if is_fn2(source, p) == 1 {
        q = p + 2
        hasfn = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    if r == 0 {
      if hasfn == 1 {
        if is_ws_at(source, q) == 0 {
          hasfn = 0
        } else {
        }
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    if r == 0 {
      if hasfn == 1 {
        q = skip_ws(source, q)
      } else {
      }
    } else {
    }
  } else {
  }
  var qe: Int = q
  if err == 0 {
    if r == 0 {
      if hasfn == 1 {
        qe = scan_name(source, q)
      } else {
      }
    } else {
    }
  } else {
  }
  var tact = 0
  if err == 0 {
    if r == 0 {
      if hasfn == 1 {
        if qe != q {
          tact = 1
        } else {
        }
      } else {
      }
    } else {
    }
  } else {
  }
  var samefirst = 0
  if tact == 1 {
    samefirst = names_equal(source, fs, fe, q, qe)
  } else {
  }
  if tact == 1 {
    if samefirst == 0 {
      r = 2
    } else {
    }
  } else {
  }
  return r
}

fn match_return_ws(source: SourceBytes, o: Int) -> Int {
  var out = o
  var err = 0
  var p = o
  if is_ret3(source, p) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    p = p + 3
  } else {
  }
  if err == 0 && is_urn3(source, p) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    p = p + 3
  } else {
  }
  if err == 0 && is_ws_at(source, p) == 0 {
    err = 1
  } else {
  }
  if err == 0 {
    p = skip_ws(source, p)
  } else {
  }
  if err == 0 {
    out = p
  } else {
  }
  return out
}

fn match_varlet_body(source: SourceBytes, o: Int) -> Int {
  var out = o
  var err = 0
  var isv = 0
  if is_var3(source, o) == 1 {
    isv = 1
  } else {
  }
  var isl = 0
  if err == 0 {
    if isv == 0 {
      if is_let3(source, o) == 1 {
        isl = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    if isv == 0 {
      if isl == 0 {
        err = 1
      } else {
      }
    } else {
    }
  } else {
  }
  var p = o
  if err == 0 {
    p = o + 3
  } else {
  }
  if err == 0 {
    if is_ws_at(source, p) == 0 {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    p = skip_ws(source, p)
  } else {
  }
  var vs = p
  var ve: Int = p
  if err == 0 {
    ve = scan_name(source, p)
  } else {
  }
  if err == 0 {
    if ve == p {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    p = ve
  } else {
  }
  if err == 0 {
    p = skip_ws(source, p)
  } else {
  }
  if err == 0 {
    if expect_byte(source, p, 61) == 0 {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    p = p + 1
  } else {
  }
  if err == 0 {
    p = skip_ws(source, p)
  } else {
  }
  var vd: Int = p
  if err == 0 {
    vd = scan_digits(source, p)
  } else {
  }
  if err == 0 {
    if vd == p {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    if 19 <= vd - p {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    p = vd
  } else {
  }
  if err == 0 {
    p = skip_ws(source, p)
  } else {
  }
  var rp: Int = p
  if err == 0 {
    rp = match_return_ws(source, p)
  } else {
  }
  if err == 0 {
    if rp == p {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    p = rp
  } else {
  }
  var rd: Int = p
  if err == 0 {
    rd = scan_digits(source, p)
  } else {
  }
  var hasdigits = 1
  if err == 0 {
    if rd == p {
      hasdigits = 0
    } else {
    }
  } else {
  }
  if hasdigits == 1 {
    if 19 <= rd - p {
      err = 1
    } else {
    }
  } else {
  }
  if hasdigits == 1 {
    p = rd
  } else {
  }
  var rs = p
  var re: Int = p
  if err == 0 {
    if hasdigits == 0 {
      re = scan_name(source, p)
    } else {
    }
  } else {
  }
  if err == 0 {
    if hasdigits == 0 {
      if re == p {
        err = 1
      } else {
      }
    } else {
    }
  } else {
  }
  var sameok = 0
  if err == 0 {
    if hasdigits == 0 {
      if names_equal(source, vs, ve, rs, re) == 1 {
        sameok = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    if hasdigits == 0 {
      if sameok == 0 {
        err = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    if hasdigits == 0 {
      p = re
    } else {
    }
  } else {
  }
  if err == 0 {
    out = p
  } else {
  }
  return out
}

fn is_unsupported_prog(source: SourceBytes) -> Int {
  var r = 0
  var n = byte_length(source)
  var err = 0
  var o = skip_ws(source, 0)
  if byte_length(source) - o <= 0 {
    err = 1
  } else {
  }
  if err == 0 && is_fn2(source, o) == 0 {
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
  var ns = o
  var ne: Int = o
  if err == 0 {
    ne = scan_name(source, o)
  } else {
  }
  if err == 0 && ne == o {
    err = 1
  } else {
  }
  if err == 0 {
    o = ne
  } else {
  }
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
  var typ = 0
  if err == 0 {
    if is_int3(source, o) == 1 {
      typ = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    if typ == 0 {
      if is_str3(source, o) == 1 {
        typ = 2
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    if typ == 0 {
      if is_bool4(source, o) == 1 {
        typ = 3
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    if typ == 0 {
      err = 1
    } else {
    }
  } else {
  }
  if err == 0 {
    if typ == 1 {
      o = o + 3
    } else {
    }
  } else {
  }
  if err == 0 {
    if typ == 2 {
      o = o + 3
    } else {
    }
  } else {
  }
  if err == 0 {
    if typ == 3 {
      o = o + 4
    } else {
    }
  } else {
  }
  if err == 0 {
    if is_ws_at(source, o) == 0 {
      if expect_byte(source, o, 123) == 0 {
        err = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if err == 0 {
    o = skip_ws(source, o)
  } else {
  }
  if err == 0 {
    if expect_byte(source, o, 123) == 0 {
      err = 1
    } else {
    }
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
  var bs = o
  var ro: Int = o
  if err == 0 {
    ro = match_return_ws(source, o)
  } else {
  }
  var hasret = 0
  if err == 0 {
    hasret = 1
  } else {
  }
  if hasret == 1 {
    if ro == o {
      hasret = 0
    } else {
    }
  } else {
  }
  var vo: Int = bs
  var vhit = 0
  if err == 0 {
    if hasret == 1 {
      if typ == 1 {
        vhit = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if vhit == 1 {
    vo = scan_value(source, ro)
  } else {
  }
  if vhit == 1 {
    if vo == ro {
      vhit = 0
    } else {
    }
  } else {
  }
  var so: Int = bs
  var strhit = 0
  if err == 0 {
    if hasret == 1 {
      if typ == 2 {
        strhit = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if strhit == 1 {
    so = scan_string(source, ro)
  } else {
  }
  if strhit == 1 {
    if so == ro {
      strhit = 0
    } else {
    }
  } else {
  }
  var tro: Int = bs
  var truehit = 0
  if err == 0 {
    if hasret == 1 {
      if typ == 3 {
        truehit = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if truehit == 1 {
    if is_true4(source, ro) == 1 {
      tro = ro + 4
    } else {
    }
  } else {
  }
  if truehit == 1 {
    if tro == bs {
      truehit = 0
    } else {
    }
  } else {
  }
  var fro: Int = bs
  var falsehit = 0
  if err == 0 {
    if hasret == 1 {
      if typ == 3 {
        falsehit = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if falsehit == 1 {
    if is_fals4(source, ro) == 1 {
      if expect_byte(source, ro + 4, 101) == 1 {
        fro = ro + 5
      } else {
      }
    } else {
    }
  } else {
  }
  if falsehit == 1 {
    if fro == bs {
      falsehit = 0
    } else {
    }
  } else {
  }
  var wo: Int = bs
  var whit = 0
  if err == 0 {
    if hasret == 0 {
      if typ == 1 {
        whit = 1
      } else {
      }
    } else {
    }
  } else {
  }
  if whit == 1 {
    wo = match_varlet_body(source, bs)
  } else {
  }
  if whit == 1 {
    if wo == bs {
      whit = 0
    } else {
    }
  } else {
  }
  var be: Int = bs
  if vhit == 1 {
    be = vo
  } else {
  }
  if strhit == 1 {
    if be == bs {
      be = so
    } else {
    }
  } else {
  }
  if truehit == 1 {
    if be == bs {
      be = tro
    } else {
    }
  } else {
  }
  if falsehit == 1 {
    if be == bs {
      be = fro
    } else {
    }
  } else {
  }
  if whit == 1 {
    if be == bs {
      be = wo
    } else {
    }
  } else {
  }
  var hasbody = 0
  if err == 0 {
    hasbody = 1
  } else {
  }
  if hasbody == 1 {
    if be == bs {
      hasbody = 0
    } else {
    }
  } else {
  }
  var t = 0
  if hasbody == 1 {
    t = match_tail(source, be, ns, ne)
  } else {
  }
  if t == 1 {
    r = 1
  } else {
  }
  if t == 2 {
    r = 1
  } else {
  }
  return r
}

fn main(source: SourceBytes) -> Int {
  var err = 0
  var neg1 = 0 - 1
  var neg2 = 0 - 2
  var neg5 = 0 - 5
  var neg6 = 0 - 6
  var h1 = find_fn(source)
  if h1 == neg1 {
    err = 1
  } else {
  }
  if h1 == neg6 {
    err = 6
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
  if h3 == neg5 {
    err = 5
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
  if err == 1 || err == 2 || err == 3 {
    if is_unsupported_prog(source) == 1 {
      err = 5
    } else {
    }
  } else {
  }
  if err == 0 {
    say("int main")
    say("(")
    say("void")
    say(")")
    say("{")
    say("return")
    say(int_text(v))
    say(";")
    say("}")
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
  if err == 5 {
    say("ERR unsupported")
  } else {
  }
  if err == 6 {
    err = 0
  } else {
  }
  return err
}
