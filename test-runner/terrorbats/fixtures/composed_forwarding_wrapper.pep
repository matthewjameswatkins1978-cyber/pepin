// Red baseline: two-level forwarding wrapper, the shape Agent 2 measured as
// exceeding the ceiling (parse/typecheck counts 3/3, zero cache hits).
fn inner(x: Int) -> Int { return x + 1 }

fn outer(x: Int) -> Int { return inner(x) }

fn main() -> Int { return outer(41) }
say(int_text(outer(41)))
