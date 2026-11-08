type Shape = Circle(Int) | Rect(Int, Int)

fn area(shape: Shape) -> Int {
    return match shape {
        Circle(radius) => 3 * radius * radius
        Rect(width, height) => width * height
    }
}

fn total(shapes: List[Shape]) -> Int {
    var sum = 0
    for shape in shapes {
        sum = sum + area(shape)
    }
    return sum
}

let gallery = [Circle(2), Rect(3, 4), Circle(1)]

say(int_text(area(Circle(2))))
say(int_text(area(Rect(3, 4))))
say(int_text(total(gallery)))
