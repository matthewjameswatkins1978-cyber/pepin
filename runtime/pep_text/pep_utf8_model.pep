# Agent-4 UTF-8 classifier model: interpreter-executed mirror of the byte
# policy transcribed into pep_utf8.c from the Pep-written lexer model.
# Widths, the E0/ED/F0/F4 second-byte ranges, and boundary values match
# `utf8_error` exactly. CLI `run` executes the top-level drivers below.
# Pep has no `<` operator, only `<=`, hence the `!(b <= a)` form.

fn utf8_width(first: Int) -> Int {
  if !(128 <= first) {
    return 1
  } else {
    return if !(194 <= first) { -1 } else { if !(224 <= first) { 2 } else { if !(240 <= first) { 3 } else { if !(245 <= first) { 4 } else { -1 } } } }
  }
}

fn utf8_lo(first: Int) -> Int {
  if first == 224 {
    return 160
  } else {
    return if first == 240 { 144 } else { 128 }
  }
}

fn utf8_hi(first: Int) -> Int {
  if first == 237 {
    return 159
  } else {
    return if first == 244 { 143 } else { 191 }
  }
}

say(int_text(utf8_width(0)))
say(int_text(utf8_width(127)))
say(int_text(utf8_width(128)))
say(int_text(utf8_width(193)))
say(int_text(utf8_width(194)))
say(int_text(utf8_width(223)))
say(int_text(utf8_width(224)))
say(int_text(utf8_width(239)))
say(int_text(utf8_width(240)))
say(int_text(utf8_width(244)))
say(int_text(utf8_width(245)))
say(int_text(utf8_width(255)))
say(int_text(utf8_lo(224)))
say(int_text(utf8_lo(240)))
say(int_text(utf8_lo(237)))
say(int_text(utf8_lo(65)))
say(int_text(utf8_hi(237)))
say(int_text(utf8_hi(244)))
say(int_text(utf8_hi(224)))
say(int_text(utf8_hi(65)))
