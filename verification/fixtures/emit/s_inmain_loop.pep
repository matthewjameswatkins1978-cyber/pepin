# S-shape A: the whole List lives inside main. Loop in main, no List crosses a
# chunk boundary, returns Int.
fn main() -> Int {
    let data = [1, 2, 3]
    var t = 0
    for v in data {
        t = t + v
    }
    return t
}