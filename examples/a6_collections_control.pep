type Point {
    x: Int
    y: Int
}

type Expr = Number(Int) | Add(Expr, Expr)

fn sum(values: List[Int]) -> Int {
    var total = 0
    for value in values {
        total = total + value
    }
    return total
}

fn sum_points(points: List[Point]) -> Int {
    var total = 0
    for point in points {
        total = total + point.x + point.y
    }
    return total
}

fn evaluate(expression: Expr) -> Int {
    return match expression {
        Number(value) => value
        Add(left, right) => evaluate(left) + evaluate(right)
    }
}

fn sum_expressions(expressions: List[Expr]) -> Int {
    var total = 0
    for expression in expressions {
        total = total + evaluate(expression)
    }
    return total
}

fn sum_rows(rows: List[List[Int]]) -> Int {
    var total = 0
    for row in rows {
        total = total + sum(row)
    }
    return total
}

fn count_down(start: Int) -> Int {
    var current = start
    while current != 0 {
        current = current - 1
    }
    return current
}

let values = [10, 12, 20]
let original: List[Int] = []
let extended = append(original, 7)
say(int_text(sum([10, 12, 20])))
say(int_text(length(original)))
say(int_text(length(extended)))
say(int_text(sum_points([Point { x: 2, y: 3 }, Point { x: 5, y: 7 }])))
say(int_text(sum_expressions([Number(10), Add(Number(5), Number(7))])))
say(int_text(sum_rows([[1, 2], [3, 4]])))
say(int_text(count_down(4)))
say(int_text(if contains(values, 12) && !(length(values) == 0) { 1 } else { 0 }))
say(int_text(if false && (1 / 0 == 0) { 1 } else { 42 }))
say(int_text(if str_contains("café", "é") { 1 } else { 0 }))
say(int_text(if str_contains("a\0b", "\0") { 1 } else { 0 }))
say(int_text(if str_contains("a\0b", "a\0b") { 1 } else { 0 }))
say(int_text(if str_contains("a\0b", "b\0c") { 1 } else { 0 }))
say(int_text(length(str_chars(""))))
say(int_text(length(str_chars("€"))))
say(int_text(length(str_chars("Aé🙂"))))
say(int_text(if contains(str_chars("é"), "́") { 1 } else { 0 }))
say(int_text(if contains(str_chars("a\0b"), "\0") { 1 } else { 0 }))