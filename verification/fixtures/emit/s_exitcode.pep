# OUTPUT WITHOUT int_text: the total is returned as the process exit code, so the
# S dispatch shape (list + loop in main, per-element cross-chunk Int call) can be
# verified natively while int_text remains unemittable. Expected exit code 6.
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