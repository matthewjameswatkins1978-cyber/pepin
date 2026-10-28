fn sum(values: List[Int]) -> Int {
    var total = 0
    for value in values {
        total = total + value
    }
    return total
}
say(int_text(sum([10, 12, 20])))
