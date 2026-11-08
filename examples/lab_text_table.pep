fn mul(first: Int, second: Int) -> Int {
    return first * second
}

fn row_total(n: Int) -> Int {
    var total = 0
    let factors = [1, 2, 3]
    for factor in factors {
        total = total + mul(n, factor)
    }
    return total
}

say("seven times one-two-three:")
say(int_text(row_total(7)))
say("nine times one-two-three:")
say(int_text(row_total(9)))
