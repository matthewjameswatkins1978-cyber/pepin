# VARIANT: List literal passed inline instead of via a local.
fn total(values: List[Int]) -> Int {
    var t = 0
    for v in values {
        t = t + v
    }
    return t
}

fn main() -> Int {
    let n = total([1, 2, 3])
    return n
}