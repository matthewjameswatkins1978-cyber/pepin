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
  [string]$Notes,
  [string]$Ids,
  [Alias('all')][switch]$AckAll
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
function Write-StateFile([string]$path, [object]$o) {
  $dir = Split-Path $path -Parent
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory $dir -Force | Out-Null }
  $tmp = "$path.tmp.$PID"
  ($o | ConvertTo-Json -Depth 8) | Out-File $tmp -Encoding utf8 -NoNewline
  Move-Item $tmp $path -Force
}
function Write-TextFileAtomic([string]$path, [string]$text) {
  # Single tmp-write + Move: the old file stays intact until the swap completes.
  $dir = Split-Path $path -Parent
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory $dir -Force | Out-Null }
  $tmp = "$path.tmp.$PID"
  # .NET write: Out-File -NoNewline would strip embedded newlines; this preserves them byte-for-byte.
  [System.IO.File]::WriteAllText($tmp, $text, [System.Text.UTF8Encoding]::new($false))
  Move-Item $tmp $path -Force
}

if (-not $State) { Fail 'MISSING_STATE' 'Pass --state <dir> for local cursor/shift store.' }
if (-not $Command) { Fail 'MISSING_COMMAND' 'One of: clock-in, clock-out, board-check, board-ack, work-orders.' }
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
    $same = @($open | Where-Object { $_.session -eq $Session })
    if ($same.Count -gt 0) {
      $dup = $same | Select-Object -Last 1
      $dup | Add-Member -NotePropertyName 'duplicate' -NotePropertyValue $true -Force
      Out-Json $dup
      return
    }
    $flagged = @()
    foreach ($s in $open) {
      if ($s.session -ne $Session) {
        $s.status = 'SUSPECT (possible crash; not inherited)'
        $flagged += $s.id
      }
    }
    if ($open.Count -gt 0) {
      # Atomic complete-state replacement: old file stays intact until Move-Item swaps it.
      $all = Get-Content $shiftsPath -Encoding utf8 | Where-Object { $_ -ne '' } | ForEach-Object { $_ | ConvertFrom-Json }
      $lines = foreach ($s in $all) {
        if ($flagged -contains $s.id) { $s.status = 'SUSPECT (possible crash; not inherited)' }
        ($s | ConvertTo-Json -Depth 8 -Compress)
      }
      Write-TextFileAtomic $shiftsPath (($lines -join "`n") + "`n")
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
    # Atomic complete-state replacement: a crash here leaves the prior record readable.
    $lines = foreach ($s in $all) {
      if ($s.id -eq $hit.id) {
        $s.status = 'CLOSED'
        $s | Add-Member -NotePropertyName 'clock_out_utc' -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o')) -Force
        $s | Add-Member -NotePropertyName 'next_action' -NotePropertyValue $Next -Force
        if ($Evidence) { $s | Add-Member -NotePropertyName 'evidence' -NotePropertyValue $Evidence -Force }
      }
      ($s | ConvertTo-Json -Depth 8 -Compress)
    }
    Write-TextFileAtomic $shiftsPath (($lines -join "`n") + "`n")
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
    $storedCursor = $null; $seen = @(); $pending = @()
    if ($stored) { $storedCursor = $stored.cursor; $seen = @($stored.seen); $pending = @($stored.pending) }
    if ($ExpectCursor -and ($storedCursor -ne $ExpectCursor)) {
      Fail 'CONFLICT' "Cursor for $Peer moved (stored='$storedCursor', expected='$ExpectCursor'). Reread and retry; a concurrent writer may have advanced it." 2
    }
    # At-least-once: unacked pending messages replay until explicitly consumed via board-ack.
    $deliver = @()
    foreach ($p in $pending) {
      $deliver += [ordered]@{ id = "$($p.id)"; untrusted = $true; redelivered = $true; content = $p.content }
    }
    $new = @(); $malformed = 0
    foreach ($m in $fed) {
      $mid = "$($m.id)"
      if ([string]::IsNullOrEmpty($mid)) { $malformed++; continue }  # id-less input is malformed data, never staged
      if ($seen -contains $mid) { continue }  # consumed: never redeliver
      if (@($pending | Where-Object { "$($_.id)" -eq $mid }).Count -gt 0) { continue }  # already staged, replayed above
      $pending += [ordered]@{ id = $mid; content = $m }
      $new += [ordered]@{ id = $mid; untrusted = $true; redelivered = $false; content = $m }
    }
    $deliver += $new
    $cursors[$Peer] = @{ cursor = $storedCursor; seen = $seen; pending = @($pending) }
    Write-StateFile $cursorPath $cursors
    Out-Json ([ordered]@{ peer = $Peer; new_messages = $deliver; cursor = $storedCursor; total_seen = $seen.Count; pending = @($pending).Count; malformed = $malformed })
  }
  'work-orders' {
    if (-not $Ledger) { Fail 'MISSING_FIELDS' 'work-orders needs --ledger <git-common-dir>/matthew-way-studio.' }
    if (-not (Test-Path $Ledger -PathType Container)) { Fail 'LEDGER_MISSING' "Ledger directory not found: $Ledger. Pass the actual <git-common-dir>/matthew-way-studio directory; do not assume zero jobs." }
    $layout = 'matthew-way-studio'
    if ((Split-Path $Ledger -Leaf) -ne 'matthew-way-studio') { $layout = "unexpected: $((Split-Path $Ledger -Leaf)) (expected <git-common-dir>/matthew-way-studio)" }
    # Studio layout (src/ledger.ts): active-job.json (unscoped/legacy snapshot)
    # plus active-job.<workerKey>.json (worker-scoped snapshots).
    $files = @()
    $files += @(Get-ChildItem (Join-Path $Ledger 'active-job.json') -ErrorAction SilentlyContinue)
    $files += @(Get-ChildItem (Join-Path $Ledger 'active-job.*.json') -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'active-job.json' })
    $jobs = @()
    foreach ($f in $files) {
      try { $j = Get-Content $f.FullName -Raw -Encoding utf8 | ConvertFrom-Json }
      catch { Fail 'LEDGER_CORRUPT' "Studio ledger file unreadable: $($f.Name). Do not invent ownership; escalate." }
      $scope = 'scoped'
      if ($f.Name -eq 'active-job.json') { $scope = 'legacy/unscoped (historical unless Studio adopts it; never a live process)' }
      $jobs += [ordered]@{
        job_id   = $j.job_id
        status   = $j.status
        owner_session = $j.worker_session_id
        branch   = $j.repo.branch
        sha      = $j.repo.current_sha
        acceptance = @($j.acceptance)
        next_action = $j.progress.next_action
        scope    = $scope
        source   = "studio-ledger:$($f.Name)"
      }
    }
    $jobsNote = $null
    if ($jobs.Count -eq 0) { $jobsNote = 'no job snapshots found - verify live Studio state; do not assume idle and do not claim work' }
    $claims = @()
    if ($Notes -and (Test-Path $Notes)) {
      $fed = Get-Content $Notes -Raw -Encoding utf8 | ConvertFrom-Json
      if ($fed -isnot [System.Array]) { $fed = @($fed) }
      foreach ($n in $fed) {
        # Note claims are advisory only: flagged, never override the ledger.
        $claims += [ordered]@{ job_id = "$($n.job_id)"; claimed_by = "$($n.claimed_by)"; untrusted = $true; verdict = 'CLAIMED-IN-NOTE (unverified)' }
      }
    }
    Out-Json ([ordered]@{ work_orders = $jobs; note_claims = $claims; ledger_path = $Ledger; ledger_layout = $layout; note = $jobsNote; authority = 'Studio ledger only; note claims never override ownership.' })
  }
  'board-ack' {
    if (-not $Peer) { Fail 'MISSING_FIELDS' 'board-ack needs --peer and --ids <a,b,...> or --all.' }
    if (-not $Ids -and -not $AckAll) { Fail 'MISSING_FIELDS' 'board-ack needs --ids <a,b,...> or --all.' }
    $cursorPath = Join-Path $State 'cursors.json'
    $cursors = Read-StateFile $cursorPath
    if (-not $cursors) { $cursors = @{} }
    if ($cursors -isnot [hashtable]) {
      $h = @{}; $cursors.PSObject.Properties | ForEach-Object { $h[$_.Name] = $_.Value }; $cursors = $h
    }
    $stored = $null
    if ($cursors.ContainsKey($Peer)) { $stored = $cursors[$Peer] }
    $storedCursor = $null; $seen = @(); $pending = @()
    if ($stored) { $storedCursor = $stored.cursor; $seen = @($stored.seen); $pending = @($stored.pending) }
    $origSeen = @($seen)
    $want = @()
    if ($AckAll) { $want = @($pending | ForEach-Object { "$($_.id)" }) }
    else { $want = @($Ids -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }) }
    $acked = @(); $keep = @()
    foreach ($p in $pending) {
      $pendId = "$($p.id)"
      if ($want -contains $pendId) {
        $acked += $pendId
        if ($seen -notcontains $pendId) { $seen += $pendId }
        $storedCursor = $pendId
      } else { $keep += $p }
    }
    $unknown = @()
    foreach ($w in $want) {
      if ($acked -notcontains $w) {
        if ($origSeen -contains $w) { $acked += $w }  # idempotent duplicate ack
        else { $unknown += $w }
      }
    }
    $cursors[$Peer] = @{ cursor = $storedCursor; seen = $seen; pending = @($keep) }
    Write-StateFile $cursorPath $cursors
    Out-Json ([ordered]@{ peer = $Peer; acked = $acked; unknown = $unknown; cursor = $storedCursor; pending = @($keep).Count })
  }
  default { Fail 'UNKNOWN_COMMAND' "Unknown command: $Command." }
}
