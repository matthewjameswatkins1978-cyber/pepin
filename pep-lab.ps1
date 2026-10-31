param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $Arguments
)
$ErrorActionPreference = 'Stop'
if (-not $Arguments -or $Arguments.Count -eq 0 -or $Arguments[0] -in @('help', '-h', '--help')) {
  Write-Output 'Pep Lab — interactive Living Prompt over the Pep seed compiler'
  Write-Output ''
  Write-Output 'Usage:'
  Write-Output '  .\pep-lab.ps1 repl --store DIR'
  Write-Output '  .\pep-lab.ps1 eval FILE'
  Write-Output '  .\pep-lab.ps1 check|inspect|holes|describe ...'
  Write-Output '  .\pep-lab.ps1 define|show|export|eval-store --store DIR ...'
  Write-Output ''
  Write-Output 'Interactive use: run the repl command directly in a terminal.'
  Write-Output 'Scripted stdin (e.g. Get-Content ... | ...) is not supported by'
  Write-Output 'PowerShell wrappers; drive python pep_lab.py from Python instead.'
  Write-Output 'See docs/PEP_LAB.md. The compiler itself stays in pep.ps1.'
  exit 0
}
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { Write-Error 'python was not found'; exit 2 }
& $Python.Source (Join-Path $PSScriptRoot 'pep_lab.py') @Arguments
exit $LASTEXITCODE
