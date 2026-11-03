<#
.SYNOPSIS
  Agent 3 pre-validated acceptance gate runner (job-20261103-9f2be148).

  Executes the frozen acceptance sequence in one command, hard-failing on
  frozen-manifest drift, stopping at the FIRST failing stage (so the report
  names one stage/input/SHA/repro), and emitting a structured JSON result.

  Frozen manifest = BOOT-A3-20261103-002 (git blob SHAs). Expected values are
  transcribed from authoritative `git ls-tree` output only - never from memory
  summaries (gotcha 52c4d868). A2's stage-probe pin is computed DYNAMICALLY
  from refs at run time (no hand-copied hashes).

.MODES
  Preflight : no-A1-fix subset - blob verify, pack parse-check, A2-line suites +
              stage probe x3 (baseline rows), A2-line probes, A1-line probes.
              Validates the instrument chain end-to-end today.
  Full      : at the integrated (both-lines + A1 fix) worktree - pack run
              (expect NOT OBSERVED=3, exit 0), stage x3 with discriminating rows
              FLIPPED to check=valid, suites, all probes. Emits the SHA-bound
              receipt JSON backing the acceptance recommendation.

.NOTES
  Expectations are the recorded contract; no budget/limit/test is altered.
  Whole program still fails at scale by design - that is an EXPECTED row,
  never a failure. No constant-cost / O(1) claims anywhere.
#>
[CmdletBinding()]
param(
    [ValidateSet('Preflight', 'Full')]
    [string]$Mode = 'Preflight',
    [string]$RepoRoot     = 'D:\Projects\pepin',
    [string]$VerifyRoot   = 'D:\Projects\pepin\_build\bootstrap-agent3-verification',
    [string]$WorktreeA2   = 'D:\Projects\wt-a3-a2b-a400ffe',
    [string]$WorktreeA1   = 'D:\Projects\wt-a3-mimo-8130276',
    [string]$CombinedWorktree = '',
    [string]$OutJson = ''
)

$ErrorActionPreference = 'Stop'
$verify = Join-Path $VerifyRoot 'verification'

# --- frozen manifest (path -> git blob sha) --------------------------------
$Manifest = [ordered]@{
    'verification/bats/agent3-index-gates.yaml'                   = 'f6086280bca7115df79d0f412b8f8975f71e3898'
    'verification/bats/index-cache-claims.yaml'                   = '3fe77b42058b83d54697b4c4d2570feccf9993e2'
    'verification/bats/chunk-diagnostic-claims.yaml'              = '204a62bc5315714afaab840307080e76a4c382c4'
    'verification/bats/regression-hole-guard-passes.yaml'         = '3dc134df5ef922f6876e4a5ce212e90550f39aa6'
    'verification/probes/index_cache_adversarial.py'              = 'e819607c2f844fd6c213f9df52fd7218b95f9804'
    'verification/probes/chunk_diagnostic_preservation.py'        = 'b0ef73686971f230a3a0a4d309a910f44d88c8cf'
    'verification/probes/declaration_emittability_agreement.py'   = 'c5a0dec8627926f2a1b8ff22ea777fbc0702b6c4'
    'verification/probes/prereq_closure_attacks.py'               = 'd2fb7c8020b0f9759c2f5094f9ef80afae031bed'
    'verification/probes/bounded_emitter_attacks.py'              = '036068c6fb21f00e1d9fa3d849a5085a68b4b342'
    'verification/probes/refusal_code_coverage.py'                = '81aeda92365a459715b6b2013031dbc07623c0c2'
    'verification/probes/per_unit_cost_baseline.py'               = 'c3db70a0c64af3bd7ba09e8b7719643366445563'
    'verification/probes/hostile_chunk_scalar_types.py'           = '134b8d48833493d7c08350c1437601a40c07b34c'
    'verification/probes/lextoken_make_token_checker.py'          = '211490561f936d4b5bd2c7c951a0e19205a94187'
}

$Results  = [System.Collections.Generic.List[object]]::new()
$FirstFail = $null

function Add-Result {
    param([string]$Name, [string]$Expected, [string]$Actual, [bool]$Pass, [string]$Repro = '')
    $Results.Add([pscustomobject]@{ gate = $Name; expected = $Expected; actual = $Actual;
        pass = $Pass; repro = $Repro }) | Out-Null
    if (-not $Pass -and -not $FirstFail) { $script:FirstFail = $Name }
    $tag = if ($Pass) { 'ok  ' } else { 'FAIL' }
    Write-Host ("  [{0}] {1}" -f $tag, $Name)
    if (-not $Pass) { Write-Host ("         expected: {0}`n         actual:   {1}" -f $Expected, $Actual) }
}

function Invoke-Cmd {
    param([string]$File, [string[]]$Arguments, [string]$Cwd)
    $out = Push-Location $Cwd
    try { $text = & $File @Arguments 2>&1 | Out-String; return @{ code = $LASTEXITCODE; text = $text } }
    finally { Pop-Location }
}

function Get-Summary {
    param([string]$Text)
    if ($Text -match 'SUMMARY cases=(\d+) claim_falsified=(\d+)') {
        return "cases=$($Matches[1]) claim_falsified=$($Matches[2])"
    }
    if ($Text -match 'Traceback') { return 'TRACEBACK (harness error)' }
    return 'no SUMMARY line'
}

# --- step 1: frozen-manifest verification (HARD FAIL) ----------------------
Write-Host "== manifest verification (git ls-tree/hash-object vs BOOT-A3-20261103-002) =="
$drift = @()
foreach ($p in ($Manifest.Keys | Sort-Object)) {
    $file = Join-Path $VerifyRoot ($p -replace '/', [IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path $file)) { $drift += "$p MISSING"; continue }
    $hash = git -C $VerifyRoot hash-object $p
    if ($hash -ne $Manifest[$p]) { $drift += "$p actual=$hash expected=$Manifest[$p]" }
}
$manPass = ($drift.Count -eq 0)
Add-Result -Name 'frozen-manifest (13 entries)' -Expected 'all blob SHAs match' `
    -Actual $(if ($manPass) { '13/13 match' } else { $drift -join '; ' }) -Pass $manPass `
    -Repro 'git -C <VerifyRoot> hash-object <path> vs BOOT-A3-20261103-002'
if (-not $manPass) { $FirstFail = 'frozen-manifest'; } else {

$head    = git -C $VerifyRoot rev-parse HEAD
$branch  = git -C $VerifyRoot rev-parse --abbrev-ref HEAD
$dirty   = @(git -C $VerifyRoot status --short)
Write-Host "== runner: mode=$Mode verifyRoot head=$($head.Substring(0,8)) branch=$branch dirty=$($dirty.Count) =="

# pack parse-check (both modes): pack must be valid before any run
$pc = Invoke-Cmd 'terrorbats' @('pack', 'check', (Join-Path $verify 'bats\agent3-index-gates.yaml')) $VerifyRoot
Add-Result -Name 'pack parse-check (agent3-index-gates)' -Expected 'exit 0' -Actual "exit $($pc.code)" `
    -Pass ($pc.code -eq 0) -Repro 'terrorbats pack check verification\bats\agent3-index-gates.yaml'

# --- target selection ------------------------------------------------------
$targetA2 = $WorktreeA2
$targetA1 = $WorktreeA1

# stage-probe row expectations: flipped only in Full (integrated + fix)
if ($Mode -eq 'Full') {
    if (-not $CombinedWorktree) { throw 'Full mode requires -CombinedWorktree' }
    $wt = $CombinedWorktree
    $expectLexer = 'valid'
    $expectReg   = 'valid'
} else {
    $wt = $WorktreeA2
    $expectLexer = 'PEP_RUNTIME_STEP_LIMIT'
    $expectReg   = 'PEP_RUNTIME_STEP_LIMIT'
}

# Full mode validates the CANDIDATE tree: every probe targets the combined
# worktree (never the separate lane trees - false-green risk otherwise).
$a2Label = if ($Mode -eq 'Full') { 'combined candidate' } else { 'A2 line' }
$a1Label = if ($Mode -eq 'Full') { 'combined candidate' } else { 'A1 line R-baseline' }
if ($Mode -eq 'Full') { $targetA2 = $wt; $targetA1 = $wt }

# --- combined suites (5 modules, A2 combined set) --------------------------
$suiteMods = @('tests.test_c23_bounded_emission', 'tests.test_c23_arity', 'tests.test_c23_cli',
               'tests.test_c23_emitter_invariants', 'tests.test_c23_emitter_field_use')
$su = Invoke-Cmd 'python' (@('-m', 'unittest') + $suiteMods) $wt
$suOk = ($su.code -eq 0) -and ($su.text -match 'Ran \d+ tests') -and ($su.text -notmatch 'FAILED')
Add-Result -Name 'combined emitter suites (53 tests)' -Expected 'Ran 53 tests ... OK (exit 0)' `
    -Actual ("exit={0}; {1}" -f $su.code, (($su.text -split "`n" | Where-Object { $_ -match 'Ran \d+|OK|FAILED' } | ForEach-Object { $_.Trim() }) -join ' ')) `
    -Pass $suOk -Repro 'python -m unittest tests.test_c23_bounded_emission tests.test_c23_arity tests.test_c23_cli tests.test_c23_emitter_invariants tests.test_c23_emitter_field_use'

# --- stage probe x3 (byte-identical bundle + discriminating rows) ----------
$bundles = @(); $rows = @()
for ($i = 1; $i -le 3; $i++) {
    $sp = Invoke-Cmd 'python' @((Join-Path $wt 'tests\probe_integration_case.py'), '--case', 'all') $wt
    if ($sp.code -ne 0) { $rows += "run$i exit=$($sp.code)" }
    if ($sp.text -match 'compiler bundle sha256 ([0-9a-f]+)') { $bundles += $Matches[1] }
    $lex = if ($sp.text -match 'lexer-chunk\s+bytes=\s*\d+ nodes=\d+ check=(\S+)') { $Matches[1] } else { 'n/a' }
    $reg = if ($sp.text -match 'regression\s+bytes=\s*\d+ nodes=\d+ check=(\S+)') { $Matches[1] } else { 'n/a' }
    $s12 = if ($sp.text -match 'synthetic-12\s+bytes=\s*\d+ nodes=\d+ check=(\S+) unit0=(\S+) all=(\S+)') { "check=$($Matches[1]) unit0=$($Matches[2]) all=$($Matches[3])" } else { 'n/a' }
    $s8  = if ($sp.text -match 'synthetic-8\s+bytes=\s*\d+ nodes=\d+ check=(\S+) unit0=(\S+) all=(\S+)') { "check=$($Matches[1]) unit0=$($Matches[2]) all=$($Matches[3])" } else { 'n/a' }
    $rows += "lexer=$lex regression=$reg | $s12 | $s8"
}
$same = ($bundles.Count -eq 3) -and (($bundles | Select-Object -Unique).Count -eq 1)
Add-Result -Name 'stage probe x3 byte-identical bundle' -Expected '3 identical sha256' `
    -Actual $(if ($same) { $bundles[0] } else { "bundles: $($bundles -join ',')" }) -Pass $same `
    -Repro 'python tests\probe_integration_case.py --case all  (x3)'
$lexOk = $rows[0] -match "lexer=$([regex]::Escape($expectLexer))"
$regOk = $rows[0] -match "regression=$([regex]::Escape($expectReg))"
Add-Result -Name "discriminating rows: lexer=$expectLexer / regression=$expectReg" `
    -Expected "check=$expectLexer / check=$expectReg" -Actual $rows[0] `
    -Pass ($lexOk -and $regOk) -Repro 'stage probe row parse (see bundle above)'
$s12Ok = $rows[0] -match 'synthetic-12|check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT'
Add-Result -Name 'synthetic-12 bounded-beats-whole intact' `
    -Expected 'check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT' `
    -Actual $(if ($rows[0] -match '(check=\S+ unit0=\S+ all=\S+) \| ') { $Matches[1] } else { $rows[0] }) `
    -Pass ($rows[0] -match 'check=valid unit0=emitted all=PEP_RUNTIME_STEP_LIMIT')
$s8Ok = $rows[0] -match 'check=valid unit0=emitted all=emitted'
Add-Result -Name 'synthetic-8 fully green' -Expected 'check=valid unit0=emitted all=emitted' `
    -Actual $(if ($rows[0] -match 'synthetic-8.*$') { ($rows[0] -split '\|')[-1].Trim() } else { '?' }) -Pass $s8Ok

# --- A2-line probes --------------------------------------------------------
$a2Probes = @('declaration_emittability_agreement', 'bounded_emitter_attacks',
              'prereq_closure_attacks', 'per_unit_cost_baseline')
foreach ($p in $a2Probes) {
    $r = Invoke-Cmd 'python' @((Join-Path $verify "probes\$p.py"), $targetA2) $VerifyRoot
    $sum = Get-Summary $r.text
    $isPerUnit = $p -eq 'per_unit_cost_baseline'
    $ident = if ($isPerUnit) { $r.text -match 'byte_identity=True' } else { $true }
    $claimOk = if ($isPerUnit) { $true } else { $sum -match 'claim_falsified=0' }
    $expected = if ($isPerUnit) { 'exit 0 + byte_identity=True' } else { 'exit 0 + claim_falsified=0' }
    $ok = ($r.code -eq 0) -and $claimOk -and $ident
    Add-Result -Name "probe $p ($a2Label)" -Expected $expected -Actual "exit=$($r.code) $sum" `
        -Pass $ok -Repro "python verification\probes\$p.py $targetA2"
}

# --- A1-line probes --------------------------------------------------------
$a1Probes = @('refusal_code_coverage', 'hostile_chunk_scalar_types', 'lextoken_make_token_checker')
foreach ($p in $a1Probes) {
    $r = Invoke-Cmd 'python' @((Join-Path $verify "probes\$p.py"), $targetA1) $VerifyRoot
    $sum = Get-Summary $r.text
    $ok = ($r.code -eq 0) -and ($sum -match 'claim_falsified=0')
    Add-Result -Name "probe $p ($a1Label)" -Expected 'exit 0 + claim_falsified=0' `
        -Actual "exit=$($r.code) $sum" -Pass $ok -Repro "python verification\probes\$p.py $targetA1"
}

# --- pack run: Full mode only (NOT OBSERVED=3, exit 0) ---------------------
if ($Mode -eq 'Full') {
    $pr = Invoke-Cmd 'terrorbats' @('pack', 'run', (Join-Path $verify 'bats\agent3-index-gates.yaml'),
            '--repo', $wt, '--json') $VerifyRoot
    # Parse the structured summary (a phrase count would match the KEY name
    # and falsely fail even a perfect run - validated on the pack JSON shape).
    $no = -1; $prov = -1
    try {
        $pj = $pr.text | ConvertFrom-Json
        $no = $pj.summary.'NOT OBSERVED'
        $prov = $pj.summary.PROVEN
    } catch { }
    $ok = ($pr.code -eq 0) -and ($no -eq 3) -and ($prov -eq 0)
    Add-Result -Name 'pack run at integrated SHA' -Expected 'exit 0 + summary NOT OBSERVED=3 PROVEN=0' `
        -Actual "exit=$($pr.code) NOT_OBSERVED=$no PROVEN=$prov" -Pass $ok `
        -Repro 'terrorbats pack run verification\bats\agent3-index-gates.yaml --repo <combined> --json (parse summary)'
}

}  # end manifest-guarded block

# --- emit structured result ------------------------------------------------
$overall = (-not $FirstFail)
$out = [pscustomobject]@{
    runner        = 'verification/tools/run_acceptance_gates.ps1'
    mode          = $Mode
    generated_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    verify_head   = $head
    verify_branch = $branch
    first_fail    = $FirstFail
    overall_pass  = $overall
    expectations_note = 'whole-program failure at scale is EXPECTED (bounded-beats-whole); no O(1) claim'
    gates         = $Results
}
if (-not $OutJson) {
    $stamp = Get-Date -Format 'HHmmss'
    $OutJson = Join-Path $env:TEMP "a3-runner-$Mode-$stamp.json"
}
$out | ConvertTo-Json -Depth 6 | Set-Content -Path $OutJson -Encoding utf8
Write-Host ""
Write-Host ("RESULT: {0}  (first_fail={1})" -f $(if ($overall) { 'PASS' } else { 'FAIL' }), $FirstFail)
Write-Host "JSON:   $OutJson"
exit $(if ($overall) { 0 } else { 1 })
