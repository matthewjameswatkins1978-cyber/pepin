type Expr = Number(Int) | Add(Expr, Expr)

fn evaluate(expr: Expr) -> Int {
    return match expr {
        Number(n) => n
        Add(a, b) => evaluate(a) + evaluate(b)
    }
}

say(int_text(evaluate(Add(Number(20), Number(22)))))
