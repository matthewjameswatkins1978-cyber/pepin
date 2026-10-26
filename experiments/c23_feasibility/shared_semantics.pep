type Point {
    x: Int
    y: Int
}
type Expr = Number(Int) | Add(Expr, Expr)

fn evaluate(expr: Expr) -> Int {
    return match expr {
        Number(value) => value
        Add(left, right) => evaluate(left) + evaluate(right)
    }
}

fn sum(items: List[Int]) -> Int {
    var total = 0
    for item in items {
        total = total + item
    }
    return total
}

fn factorial(value: Int) -> Int {
    if value == 0 {
        return 1
    } else {
        return value * factorial(value - 1)
    }
}

fn sum_to(value: Int) -> Int {
    var total = 0
    var current = 1
    while current <= value {
        total = total + current
        current = current + 1
    }
    return total
}

let point = Point { x: 20, y: 22 }
let expr = Add(Number(point.x), Number(point.y))
say(int_text(evaluate(expr)))
say(int_text(point.x + point.y))
say(int_text(sum([10, 12, 20])))
say(int_text(sum([10, 12, 20, 7])))
say(int_text(factorial(5)))
say(int_text(sum_to(100)))
