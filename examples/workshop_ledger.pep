type Entry = Named(Int, Int)

fn entry_value(entry: Entry) -> Int {
    return match entry {
        Named(_, amount) => amount
    }
}

fn total(entries: List[Entry]) -> Int {
    var sum = 0
    for entry in entries {
        sum = sum + entry_value(entry)
    }
    return sum
}

fn largest(entries: List[Entry]) -> Int {
    var best = 0
    for entry in entries {
        var amount = entry_value(entry)
        if !(amount <= best) {
            best = amount
        } else {
            best = best
        }
    }
    return best
}

fn count_over(entries: List[Entry], limit: Int) -> Int {
    var found = 0
    for entry in entries {
        if !(entry_value(entry) <= limit) {
            found = found + 1
        } else {
            found = found
        }
    }
    return found
}

let day = [Named(1, 40), Named(2, 7), Named(3, 15)]

say("total:")
say(int_text(total(day)))
say("largest:")
say(int_text(largest(day)))
say("over 10:")
say(int_text(count_over(day, 10)))
