let MULTIPLIER: Int = 10
let GREETING: Str = "Pepin Native Power"

fn scale(x: Int) -> Int {
  return x * MULTIPLIER
}

fn message() -> Str {
  return GREETING
}

say(message())
say(int_text(scale(42)))
