type Expr = Number(Int) | Add(Expr, Expr)
fn evaluate(expr: Expr) -> Int {
    return match expr {
        Number(n) => n
    }
}
