# Agent-4 text-buffer capacity model: full policy in Pep, interpreter-executed.
# The v2 tool-host front end (parser/checker as tools, 100k-step budget)
# currently fits only ~450-byte programs, so the tool path verifies the
# minimal core in pep_textbuf_core.pep. This file carries the complete
# model — saturating double step, clamped growth, looping growth driver,
# and the int_width digit cascade — executed here by the CLI interpreter
# (1M-step budget) through top-level drivers below. CLI `run` executes
# top-level statements; fn main is the C23 emitter convention.
# Pep has no `<` operator, only `<=`, hence the `!(b <= a)` form.

fn grow_step(cap: Int) -> Int {
  let half = 4611686018427387903
  let maxint = 9223372036854775807
  if !(cap <= half) {
    return maxint
  } else {
    return cap + cap
  }
}

fn grow_clamped(cap: Int, needed: Int) -> Int {
  let floor = 8
  let sane_cap = if !(0 <= cap) { 0 } else { cap }
  let stepped = grow_step(sane_cap)
  let want = if !(0 <= needed) { 0 } else { needed }
  let covered = if !(want <= stepped) { want } else { stepped }
  if !(floor <= covered) {
    return floor
  } else {
    return covered
  }
}

fn digit_width_big(mag: Int) -> Int {
  if !(10000000000 <= mag) {
    return 10
  } else {
    return if !(100000000000 <= mag) { 11 } else { if !(1000000000000 <= mag) { 12 } else { if !(10000000000000 <= mag) { 13 } else { if !(100000000000000 <= mag) { 14 } else { if !(1000000000000000 <= mag) { 15 } else { if !(10000000000000000 <= mag) { 16 } else { if !(100000000000000000 <= mag) { 17 } else { if !(1000000000000000000 <= mag) { 18 } else { 19 } } } } } } } }
  }
}

fn digit_width(mag: Int) -> Int {
  if !(10 <= mag) {
    return 1
  } else {
    return if !(1000000000 <= mag) { digit_width_small(mag) } else { digit_width_big(mag) }
  }
}

fn digit_width_small(mag: Int) -> Int {
  if !(100 <= mag) {
    return 2
  } else {
    return if !(1000 <= mag) { 3 } else { if !(10000 <= mag) { 4 } else { if !(100000 <= mag) { 5 } else { if !(1000000 <= mag) { 6 } else { if !(10000000 <= mag) { 7 } else { if !(100000000 <= mag) { 8 } else { 9 } } } } } }
  }
}

fn int_width(value: Int) -> Int {
  let minint = 0 - 9223372036854775807 - 1
  if value == minint {
    return 20
  } else {
    return if !(0 <= value) { digit_width(0 - value) + 1 } else { digit_width(value) }
  }
}

fn next_capacity(cap: Int, needed: Int) -> Int {
  var floor = 8
  var half = 4611686018427387903
  var maxint = 9223372036854775807
  var current = if !(floor <= cap) { floor } else { cap }
  var want = if !(0 <= needed) { 0 } else { needed }
  while !(want <= current) {
    if !(current <= half) {
      current = maxint
    } else {
      current = current + current
    }
  }
  return current
}

say(int_text(next_capacity(0, 100)))
say(int_text(next_capacity(64, 40)))
say(int_text(next_capacity(-5, -3)))
say(int_text(next_capacity(4611686018427387904, 9223372036854775807)))
say(int_text(grow_clamped(-4, 3)))
say(int_text(grow_clamped(8, 100)))
say(int_text(grow_clamped(64, 40)))
say(int_text(grow_step(1024)))
say(int_text(int_width(0)))
say(int_text(int_width(9)))
say(int_text(int_width(10)))
say(int_text(int_width(-42)))
say(int_text(int_width(9223372036854775807)))
say(int_text(int_width(0 - 9223372036854775807 - 1)))
