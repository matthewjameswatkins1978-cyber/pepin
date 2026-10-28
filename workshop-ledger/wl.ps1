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
  default { Fail 'UNKNOWN_COMMAND' "Unknown command: $Command." }
}
