# S-shape B (the critical one): list stays in main, loop in main, and a
# cross-chunk Int-returning helper is called once per element. If this emits,
# route S survives without any List-argument lowering.
fn add(a: Int, b: Int) -> Int {
    let s = a + b
    return s
}

fn main() -> Int {
    let data = [1, 2, 3]
    var t = 0
    for v in data {
        t = add(t, v)
    }
    return t
}