fn count_down(start: Int) -> Int {
    var current = start
    while current != 0 {
        current = current - 1
    }
    return current
}
say(int_text(count_down(3)))
say("done")
