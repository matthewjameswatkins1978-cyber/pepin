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

pub fn sum_prefix_squares(values: List[Int], count: Int) -> Int {
    if count <= 0 { return 0 }
    let size = length(values)
    var index = 0
    var total = 0
    while index < size {
        if index >= count { break }
        total = total + square(values[index])
        index = index + 1
    }
    return total
}
