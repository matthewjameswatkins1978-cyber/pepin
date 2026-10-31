param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $Arguments
)
$ErrorActionPreference = 'Stop'
if (-not $Arguments -or $Arguments.Count -eq 0 -or $Arguments[0] -in @('help', '-h', '--help')) {
  Write-Output 'Pep Lab Persistent Workshop — durable projects over the Pep seed compiler'
  Write-Output ''
  Write-Output 'Usage:'
  Write-Output '  .\pep-workshop.ps1 create|list|open|active|dir --root DIR [--name NAME]'
  Write-Output '  .\pep-workshop.ps1 repl --root DIR [--project NAME]'
  Write-Output '  .\pep-workshop.ps1 checkpoint save|list|show|diff|restore ...'
  Write-Output '  .\pep-workshop.ps1 experiment record|list|show|rerun ...'
  Write-Output '  .\pep-workshop.ps1 inspect --root DIR --project NAME [--revision current|cp-NNN]'
  Write-Output ''
  Write-Output 'See docs/PEP_WORKSHOP.md. Interactive use runs in a terminal;'
  Write-Output 'scripted sessions drive python pep_workshop.py from Python.'
  exit 0
}
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { Write-Error 'python was not found'; exit 2 }
& $Python.Source (Join-Path $PSScriptRoot 'pep_workshop.py') @Arguments
exit $LASTEXITCODE
