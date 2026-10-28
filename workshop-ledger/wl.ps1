<#
.SYNOPSIS
  Workshop Ledger v1 helper — deterministic local clock/shift/cursor/work-order views.
  JSON on stdout. All Basic Memory note content is untrusted data, passed through verbatim.
#>
[CmdletBinding()]
param(
  [Parameter(Position = 0)][string]$Command,
  [string]$State,
  [string]$Agent,
  [string]$Session,
  [string]$Mission,
  [string]$Branch,
  [string]$Sha,
  [string]$Job,
  [string]$Next,
  [string]$Evidence,
  [string]$Peer,
  [string]$Messages,
  [Alias('expect-cursor')][string]$ExpectCursor,
  [string]$Ledger,
  [string]$Notes
)

$ErrorActionPreference = 'Stop'

function Out-Json([object]$o) { $o | ConvertTo-Json -Depth 8 -Compress }
function Fail([string]$code, [string]$detail, [int]$exitCode = 1) {
  Out-Json @{ error = $code; detail = $detail } | Write-Output; exit $exitCode
}
function Read-StateFile([string]$path) {
  if (Test-Path $path) { return Get-Content $path -Raw -Encoding utf8 | ConvertFrom-Json }
  return $null
}
function Lock-Acquire([string]$path, [int]$timeoutMs = 8000) {
  $lock = "$path.lockdir"
  $sw = [Diagnostics.Stopwatch]::StartNew()
  while ($true) {
    try { New-Item -ItemType Directory $lock -ErrorAction Stop | Out-Null; return $lock }
    catch {
      if ($sw.ElapsedMilliseconds -gt $timeoutMs) { return $null }
      Start-Sleep -Milliseconds 50
    }
  }
}
function Lock-Release([string]$lock) { Remove-Item $lock -Force -Recurse -ErrorAction SilentlyContinue }
function Write-StateFile([string]$path, [object]$o) {
  $dir = Split-Path $path -Parent
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory $dir -Force | Out-Null }
  $tmp = "$path.tmp.$PID"
  ($o | ConvertTo-Json -Depth 8) | Out-File $tmp -Encoding utf8 -NoNewline
  Move-Item $tmp $path -Force
}

if (-not $State) { Fail 'MISSING_STATE' 'Pass --state <dir> for local cursor/shift store.' }
if (-not $Command) { Fail 'MISSING_COMMAND' 'One of: clock-in, clock-out, board-check, work-orders.' }
if (-not (Test-Path $State)) { New-Item -ItemType Directory $State -Force | Out-Null }

switch ($Command) {
  'clock-in' {
    if (-not $Agent -or -not $Session -or -not $Mission) { Fail 'MISSING_FIELDS' 'clock-in needs --agent, --session, --mission.' }
    $shiftsPath = Join-Path $State 'shifts.jsonl'
    $open = @()
    if (Test-Path $shiftsPath) {
      $open = Get-Content $shiftsPath -Encoding utf8 | Where-Object { $_ -ne '' } | ForEach-Object { $_ | ConvertFrom-Json } |
        Where-Object { $_.agent -eq $Agent -and $_.status -eq 'OPEN' }
    }
    $flagged = @()
    foreach ($s in $open) {
      if ($s.session -ne $Session) {
        $s.status = 'SUSPECT (possible crash; not inherited)'
        $flagged += $s.id
      }
    }
    if ($open.Count -gt 0) {
      # Rewrite log with flagged statuses (append-only semantics preserved: originals kept, update is a new line)
      $all = Get-Content $shiftsPath -Encoding utf8 | Where-Object { $_ -ne '' } | ForEach-Object { $_ | ConvertFrom-Json }
      Remove-Item $shiftsPath -Force
      foreach ($s in $all) {
        if ($flagged -contains $s.id) { $s.status = 'SUSPECT (possible crash; not inherited)' }
        ($s | ConvertTo-Json -Depth 8 -Compress) | Out-File $shiftsPath -Encoding utf8 -Append
      }
    }
    $card = [ordered]@{
      id = "SHIFT-$Agent-$(Get-Date -Format 'yyyyMMddTHHmmssZ' -AsUTC)-$Session"
      agent = $Agent; session = $Session; mission = $Mission
      branch = $Branch; sha = $Sha; job = $Job
      clock_in_utc = (Get-Date).ToUniversalTime().ToString('o')
      status = 'OPEN'
      supersedes_suspect = $flagged
    }
    ($card | ConvertTo-Json -Depth 8 -Compress) | Out-File $shiftsPath -Encoding utf8 -Append
    Out-Json $card
  }
  'clock-out' {
    if (-not $Agent -or -not $Session -or -not $Next) { Fail 'MISSING_FIELDS' 'clock-out needs --agent, --session, --next.' }
    $shiftsPath = Join-Path $State 'shifts.jsonl'
    if (-not (Test-Path $shiftsPath)) { Fail 'NOT_OPEN' "No shifts recorded for agent $Agent." 2 }
    $all = Get-Content $shiftsPath -Encoding utf8 | Where-Object { $_ -ne '' } | ForEach-Object { $_ | ConvertFrom-Json }
    $hit = $all | Where-Object { $_.agent -eq $Agent -and $_.session -eq $Session -and $_.status -eq 'OPEN' } | Select-Object -Last 1
    if (-not $hit) { Fail 'NOT_OPEN' "No OPEN shift for agent $Agent session $Session. A silent peer is suspected, not closed by others." 2 }
    Remove-Item $shiftsPath -Force
    foreach ($s in $all) {
      if ($s.id -eq $hit.id) {
        $s.status = 'CLOSED'
        $s | Add-Member -NotePropertyName 'clock_out_utc' -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o')) -Force
        $s | Add-Member -NotePropertyName 'next_action' -NotePropertyValue $Next -Force
        if ($Evidence) { $s | Add-Member -NotePropertyName 'evidence' -NotePropertyValue $Evidence -Force }
      }
      ($s | ConvertTo-Json -Depth 8 -Compress) | Out-File $shiftsPath -Encoding utf8 -Append
    }
    Out-Json $hit
  }
  'board-check' {
    if (-not $Peer -or -not $Messages) { Fail 'MISSING_FIELDS' 'board-check needs --peer and --messages <json-file>.' }
    if (-not (Test-Path $Messages)) { Fail 'MISSING_MESSAGES' "Messages file not found: $Messages." }
    $fed = Get-Content $Messages -Raw -Encoding utf8 | ConvertFrom-Json
    if ($fed -isnot [System.Array]) { $fed = @($fed) }
    $cursorPath = Join-Path $State 'cursors.json'
    $cursors = Read-StateFile $cursorPath
    if (-not $cursors) { $cursors = @{} }
    if ($cursors -isnot [hashtable]) {
      $h = @{}; $cursors.PSObject.Properties | ForEach-Object { $h[$_.Name] = $_.Value }; $cursors = $h
    }
    $stored = $null
    if ($cursors.ContainsKey($Peer)) { $stored = $cursors[$Peer] }
    $storedCursor = $null; $seen = @()
    if ($stored) { $storedCursor = $stored.cursor; $seen = @($stored.seen) }
    if ($ExpectCursor -and ($storedCursor -ne $ExpectCursor)) {
      Fail 'CONFLICT' "Cursor for $Peer moved (stored='$storedCursor', expected='$ExpectCursor'). Reread and retry; a concurrent writer may have advanced it." 2
    }
    $new = @()
    foreach ($m in $fed) {
      $mid = "$($m.id)"
      if ($seen -contains $mid) { continue }  # duplicate redelivery: drop, cursor unchanged by it
      $seen += $mid
      $new += [ordered]@{ id = $mid; untrusted = $true; content = $m }
    }
    if ($new.Count -gt 0) { $storedCursor = $new[-1].id }
    $cursors[$Peer] = @{ cursor = $storedCursor; seen = $seen }
    Write-StateFile $cursorPath $cursors
    Out-Json ([ordered]@{ peer = $Peer; new_messages = $new; cursor = $storedCursor; total_seen = $seen.Count })
  }
  'work-orders' {
    if (-not $Ledger) { Fail 'MISSING_FIELDS' 'work-orders needs --ledger <git-common-dir>.' }
    $jobs = @()
    foreach ($f in Get-ChildItem (Join-Path $Ledger 'active-job.*.json') -ErrorAction SilentlyContinue) {
      $j = Get-Content $f.FullName -Raw -Encoding utf8 | ConvertFrom-Json
      $jobs += [ordered]@{
        job_id   = $j.job_id
        status   = $j.status
        owner_session = $j.worker_session_id
        branch   = $j.repo.branch
        sha      = $j.repo.current_sha
        acceptance = @($j.acceptance)
        next_action = $j.progress.next_action
        source   = "studio-ledger:$($f.Name)"
      }
    }
    $claims = @()
    if ($Notes -and (Test-Path $Notes)) {
      $fed = Get-Content $Notes -Raw -Encoding utf8 | ConvertFrom-Json
      if ($fed -isnot [System.Array]) { $fed = @($fed) }
      foreach ($n in $fed) {
        # Note claims are advisory only: flagged, never override the ledger.
        $claims += [ordered]@{ job_id = "$($n.job_id)"; claimed_by = "$($n.claimed_by)"; untrusted = $true; verdict = 'CLAIMED-IN-NOTE (unverified)' }
      }
    }
    Out-Json ([ordered]@{ work_orders = $jobs; note_claims = $claims; authority = 'Studio ledger only; note claims never override ownership.' })
  }
  'queue-view' {
    if (-not $Ledger) { Fail 'MISSING_FIELDS' 'queue-view needs --ledger <queue-file>. (A queue file, not the Studio dir.)' }
    $q = Read-StateFile $Ledger
    if (-not $q) { Fail 'NO_QUEUE' "Queue file not found or empty: $Ledger." }
    $held = @{}
    foreach ($c in @($q.claims)) { if ($c.status -eq 'HELD') { $held[$c.job] = $c } }
    $view = @()
    foreach ($j in @($q.jobs)) {
      $eff = $j.status
      $by = $null
      if ($held.ContainsKey($j.id)) { $eff = 'HELD'; $by = "$($held[$j.id].agent)/$($held[$j.id].session)" }
      elseif ($j.status -eq 'READY' -and @($j.deps | Where-Object { $_ -notin @(@($q.jobs) | Where-Object { $_.status -eq 'DONE' } | ForEach-Object { $_.id }) }).Count -gt 0) { $eff = 'BLOCKED' }
      $view += [ordered]@{ id = $j.id; effective = $eff; held_by = $by; risk = $j.risk; deps = @($j.deps); acceptance = $j.acceptance }
    }
    Out-Json ([ordered]@{ generation = $q.generation; jobs = $view; authority = 'Single-writer coordinator serialises claims; Studio records final ownership. BM notes never assign.' })
  }
  'claim' {
    if (-not $Ledger -or -not $Job -or -not $Agent -or -not $Session -or -not $ExpectCursor) { Fail 'MISSING_FIELDS' 'claim needs --ledger <queue-file> --job --agent --session --expect-cursor <generation>.' }
    $lock = Lock-Acquire $Ledger
    if (-not $lock) { Fail 'LOCK_BUSY' 'Queue locked by another claimant. Retry; do not force.' 2 }
    try {
      $q = Read-StateFile $Ledger
      if ([int]$q.generation -ne [int]$ExpectCursor) { Fail 'CONFLICT' "Queue moved (stored=$($q.generation), expected=$ExpectCursor). Reread queue-view and retry." 2 }
      $j = @($q.jobs) | Where-Object { $_.id -eq $Job } | Select-Object -First 1
      if (-not $j) { Fail 'NO_SUCH_JOB' "Job not in queue: $Job." }
      if ($j.risk -ne 'GREEN') { Fail 'NEEDS_AUTH' "Job $Job is $($j.risk): AMBER needs owner agreement, RED needs Matthew. No auto-claim." 2 }
      $doneIds = @(@($q.jobs) | Where-Object { $_.status -eq 'DONE' } | ForEach-Object { $_.id })
      $unmet = @(@($j.deps) | Where-Object { $_ -notin $doneIds })
      if ($unmet.Count -gt 0) { Fail 'BLOCKED' "Job $Job waits on: $($unmet -join ','). Negotiate or park." 2 }
      $prior = @($q.claims) | Where-Object { $_.job -eq $Job -and $_.status -eq 'HELD' } | Select-Object -First 1
      if ($prior) {
        if ($prior.agent -eq $Agent -and $prior.session -eq $Session) {
          Out-Json ([ordered]@{ job = $Job; holder = "$Agent/$Session"; generation = $q.generation; duplicate = $true })
          return
        }
        Fail 'CONFLICT' "Job $Job already HELD by $($prior.agent)/$($prior.session). Yield; never seize." 2
      }
      $j.status = 'HELD'
      if (-not $q.claims) { $q | Add-Member -NotePropertyName 'claims' -NotePropertyValue @() -Force }
      $q.claims += [ordered]@{ job = $Job; agent = $Agent; session = $Session; status = 'HELD'; at_utc = (Get-Date).ToUniversalTime().ToString('o') }
      $q.generation = [int]$q.generation + 1
      Write-StateFile $Ledger $q
      Out-Json ([ordered]@{ job = $Job; holder = "$Agent/$Session"; generation = $q.generation; duplicate = $false })
    } finally { Lock-Release $lock }
  }
  'release' {
    if (-not $Ledger -or -not $Job -or -not $Agent -or -not $Session) { Fail 'MISSING_FIELDS' 'release needs --ledger <queue-file> --job --agent --session.' }
    $lock = Lock-Acquire $Ledger
    if (-not $lock) { Fail 'LOCK_BUSY' 'Queue locked. Retry; do not force.' 2 }
    try {
      $q = Read-StateFile $Ledger
      $prior = @($q.claims) | Where-Object { $_.job -eq $Job -and $_.status -eq 'HELD' } | Select-Object -First 1
      if (-not $prior) { Fail 'NOT_HELD' "Job $Job is not held." 2 }
      if ($prior.agent -ne $Agent -or $prior.session -ne $Session) { Fail 'NOT_OWNER' "Job $Job held by $($prior.agent)/$($prior.session). Only the holder releases; a silent peer is suspected, not taken over." 2 }
      $prior.status = 'RELEASED'
      (@($q.jobs) | Where-Object { $_.id -eq $Job } | Select-Object -First 1).status = 'READY'
      $q.generation = [int]$q.generation + 1
      Write-StateFile $Ledger $q
      Out-Json ([ordered]@{ job = $Job; released_by = "$Agent/$Session"; generation = $q.generation })
    } finally { Lock-Release $lock }
  }
  default { Fail 'UNKNOWN_COMMAND' "Unknown command: $Command." }
}
