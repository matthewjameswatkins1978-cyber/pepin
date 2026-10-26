type Finding {
    kind: Str
    symbolId: Int
    functionName: Str
    startByte: Int
    endByte: Int
    explanation: Str
}

type AnalysisReport {
    targetDocument: Str
    targetRevision: Str
    protocol: Int
    rootPolicy: Str
    targetStatus: Str
    authoritative: Bool
    findings: List[Finding]
}

fn analyze() -> AnalysisReport {
    let program = semantic_snapshot()
    if program.status == "valid" {
        var reachable: List[Int] = program.roots
        var changed = true
        while changed {
            changed = false
            for edge in program.calls {
                if contains(reachable, edge.caller) && !contains(reachable, edge.callee) {
                    reachable = append(reachable, edge.callee)
                    changed = true
                } else {}
            }
        }
        var findings: List[Finding] = []
        for function in program.functions {
            if !contains(reachable, function.id) {
                findings = append(findings, Finding {
                    kind: "unreachable_function",
                    symbolId: function.id,
                    functionName: function.name,
                    startByte: function.startByte,
                    endByte: function.endByte,
                    explanation: "No root-reachable call path reaches this function."
                })
            } else {}
        }
        return AnalysisReport {
            targetDocument: program.document,
            targetRevision: program.revision,
            protocol: 2,
            rootPolicy: "top_level_calls_plus_host_entry_functions",
            targetStatus: program.status,
            authoritative: true,
            findings: findings
        }
    } else {
        return AnalysisReport {
            targetDocument: program.document,
            targetRevision: program.revision,
            protocol: 2,
            rootPolicy: "top_level_calls_plus_host_entry_functions",
            targetStatus: program.status,
            authoritative: false,
            findings: []
        }
    }
}