type Expr = Number(Int) | Add(Expr, Expr)

fn evaluate(expr: Expr) -> Int {
    return match expr {
        Number(n) => ?number_case
        Add(a, b) => ?addition_case
    }
}
