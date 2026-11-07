# CONTROL: cross-chunk Int-returning call with an Int argument. If this fails too,
# the harness's call-fact plumbing is at fault and no List conclusion is valid.
fn double(x: Int) -> Int {
    var y = x
    y = y + y
    return y
}

fn main() -> Int {
    let a = 2
    let b = double(a)
    return b
}