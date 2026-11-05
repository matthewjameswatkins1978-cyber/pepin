#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Verify a claimed workshop commit SHA locally and against a remote branch,
  with PowerShell-safe exit-code handling (Workshop Signal v0.1, T1/T2).

.DESCRIPTION
  Prints a structured existence report and exits 0 only when the SHA resolves
  to a commit object locally AND (when -RemoteBranch is given) the remote
  branch head is known and ancestry is established. Every git exit code is
  captured on the line immediately following the call and printed — never
  swallowed by PowerShell conditionals (cf. BOOT-A3-20261104-073: a cat-file
  inside an `if` reported a real SHA absent).

  Reports UNKNOWN rather than fabricating success when git, the network, or
  the remote is unavailable (T7).

.PARAMETER Sha
  Full or abbreviated SHA claimed to be published.

.PARAMETER RemoteBranch
  Optional remote branch the SHA is claimed to be on/published under.

.PARAMETER Remote
  Remote name. Default 'origin'.

.PARAMETER Repo
  Repository path. Default current directory.

.EXAMPLE
  ./scripts/Confirm-WorkshopSha.ps1 -Sha 9e32999
  # -> NOT-FOUND, exit 1 (T1)

.EXAMPLE
  ./scripts/Confirm-WorkshopSha.ps1 -Sha 727f8af -RemoteBranch codex/p1-checker-cost-fix
  # -> commit + subject + on-remote + ancestry, exit 0 on success (T2)
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Sha,
  [string]$RemoteBranch = "",
  [string]$Remote = "origin",
  [string]$Repo = "."
)

$report = [ordered]@{
  sha          = $Sha
  local_type   = "UNKNOWN"
  subject      = ""
  local_code   = -1
  remote_branch = $RemoteBranch
  remote_sha   = ""
  on_remote    = "UNKNOWN"
  remote_code  = -1
  ancestry     = "UNKNOWN"
  verdict      = "NOT-VERIFIED"
}

Push-Location $Repo
try {
  # 1. Local object existence. Capture $LASTEXITCODE on the NEXT line.
  $typeOut = git cat-file -t $Sha 2>&1
  $report.local_code = $LASTEXITCODE
  if ($report.local_code -eq 0) {
    $report.local_type = "$typeOut".Trim()
    $subj = git log -1 --format=%s $Sha 2>&1
    $sc = $LASTEXITCODE
    if ($sc -eq 0) { $report.subject = "$subj".Trim() }
  } else {
    $report.local_type = "NOT-FOUND"
  }

  # 2. Remote branch head (only meaningful if the local object exists).
  if ($RemoteBranch -ne "" -and $report.local_code -eq 0) {
    $ls = git ls-remote $Remote "refs/heads/$RemoteBranch" 2>&1
    $report.remote_code = $LASTEXITCODE
    if ($report.remote_code -eq 0 -and "$ls".Trim() -ne "") {
      $report.remote_sha = ("$ls".Trim() -split '\s+')[0]
      $prefix = $report.remote_sha.StartsWith($Sha) -or $Sha.StartsWith($report.remote_sha.Substring(0, [Math]::Min(7, $report.remote_sha.Length)))
      # Ancestry: a remote branch advancing does not invalidate a historical
      # commit still in its ancestry — check merge-base, not equality.
      $null = git merge-base --is-ancestor $Sha $report.remote_sha 2>&1
      $ac = $LASTEXITCODE
      if ($ac -eq 0) {
        $report.ancestry = "ANCESTOR-OF-REMOTE-HEAD"
        $report.on_remote = "true"
      } elseif ($report.remote_sha.StartsWith($Sha) -or $Sha -eq $report.remote_sha) {
        $report.ancestry = "EQUALS-REMOTE-HEAD"
        $report.on_remote = "true"
      } else {
        $report.ancestry = "NOT-IN-REMOTE-HISTORY"
        $report.on_remote = "false"
        $prefix = $false
      }
    } elseif ($report.remote_code -eq 0) {
      $report.on_remote = "false"
      $report.ancestry = "BRANCH-NOT-FOUND"
    } else {
      $report.on_remote = "UNKNOWN"
      $report.ancestry = "REMOTE-UNREACHABLE"
    }
  }

  if ($report.local_code -eq 0 -and $report.local_type -eq "commit" `
      -and ($RemoteBranch -eq "" -or $report.on_remote -eq "true")) {
    $report.verdict = "VERIFIED"
  } elseif ($report.local_code -ne 0) {
    $report.verdict = "NOT-FOUND"
  }
} finally {
  Pop-Location
}

$report.GetEnumerator() | ForEach-Object { "{0}: {1}" -f $_.Key, $_.Value }
if ($report.verdict -eq "VERIFIED") { exit 0 } else { exit 1 }
