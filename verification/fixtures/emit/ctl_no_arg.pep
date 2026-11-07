# CONTROL: cross-chunk call with NO arguments.
fn five() -> Int {
    var z = 5
    return z
}

fn main() -> Int {
    let k = five()
    return k
}