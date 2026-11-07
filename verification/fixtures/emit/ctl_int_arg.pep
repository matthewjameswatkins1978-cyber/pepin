# CONTROL: cross-chunk Int-returning call with an Int argument. If this fails too,
# the harness's call-fact plumbing is at fault and no List conclusion is valid.
fn double(x: Int) -> Int {
    let y = x + x
    return y
}

fn main() -> Int {
    let a = 2
    let b = double(a)
    return b
}