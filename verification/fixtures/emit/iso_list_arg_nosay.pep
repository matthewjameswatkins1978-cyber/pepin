# ISOLATION: the List-argument call with NO int_text/say anywhere.
fn total(values: List[Int]) -> Int {
    var t = 0
    for v in values {
        t = t + v
    }
    return t
}

fn main() -> Int {
    let data = [1, 2, 3]
    let n = total(data)
    return n
}