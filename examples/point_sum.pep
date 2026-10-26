type Point {
    x: Int
    y: Int
}

fn sum(point: Point) -> Int {
    return point.x + point.y
}

let point = Point {
    x: 20,
    y: 22
}

say(int_text(sum(point)))
