type Shape = Circle(Int) | Rect(Int, Int) | Square(Int)

fn area(shape: Shape) -> Int {
    return match shape {
        Circle(radius) => 3 * radius * radius
        Rect(width, height) => width * height
        Square(side) => side * side
    }
}

fn perimeter(shape: Shape) -> Int {
    return match shape {
        Circle(radius) => 6 * radius
        Rect(width, height) => 2 * (width + height)
        Square(side) => 4 * side
    }
}

fn is_circle(shape: Shape) -> Int {
    return match shape {
        Circle(_) => 1
        _ => 0
    }
}

fn count_circles(shapes: List[Shape]) -> Int {
    var found = 0
    for shape in shapes {
        found = found + is_circle(shape)
    }
    return found
}

fn total_area(shapes: List[Shape]) -> Int {
    var sum = 0
    for shape in shapes {
        sum = sum + area(shape)
    }
    return sum
}

let gallery = [Circle(2), Rect(3, 4), Square(3), Circle(1)]

say("areas:")
say(int_text(area(Circle(2))))
say(int_text(area(Rect(3, 4))))
say(int_text(area(Square(3))))
say("perimeters:")
say(int_text(perimeter(Circle(2))))
say(int_text(perimeter(Rect(3, 4))))
say("circles:")
say(int_text(count_circles(gallery)))
say("gallery area:")
say(int_text(total_area(gallery)))
