# Durable reproduction of A1/A4's claimed native List pass (BOOT-A3-060).
# A1 reported this shape passing natively 4/4 but left the driver in gitignored
# _build/, so the claim had no committed artifact. This fixture is the input;
# verification/probes/emit_any_049.py --run is the durable driver.
#
# S-shape under test: List construction by literal, for-in over a List parameter,
# and a cross-chunk Int-returning call whose argument is hoisted (A1 measured that
# nested-arg calls do NOT dodge, so the call result must be bound first).
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
    let text = int_text(n)
    say(text)
    return 0
}