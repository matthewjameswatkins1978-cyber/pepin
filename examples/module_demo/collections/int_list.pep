fn square(value: Int) -> Int {
    return value * value
}

pub fn sum_squares(values: List[Int]) -> Int {
    var total = 0
    for value in values {
        total = total + square(value)
    }
    return total
}
