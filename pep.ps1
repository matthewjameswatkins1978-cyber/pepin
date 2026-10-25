param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $Arguments
)
$ErrorActionPreference = 'Stop'
if ($Arguments -and $Arguments.Count -gt 0 -and $Arguments[0] -in @('help', '-h', '--help')) {
  Write-Output 'Pep — inspect, check, query, and run plaintext .pep programs'
  Write-Output ''
  Write-Output 'Usage:'
  Write-Output '  .\pep.ps1 describe [--json]'
  Write-Output '  .\pep.ps1 inspect FILE [--json]'
  Write-Output '  .\pep.ps1 check FILE [--json]'
  Write-Output '  .\pep.ps1 query FILE --holes --json [--offset BYTE]'
  Write-Output '  .\pep.ps1 run FILE'
  Write-Output ''
  Write-Output 'Use query to inspect typed holes and compatible in-scope bindings.'
  exit 0
}
if (-not $Arguments -or $Arguments.Count -eq 0) {
  Write-Error 'usage: .\pep.ps1 --help'
  exit 2
}
$Command = $Arguments[0]
if ($Command -notin @('describe', 'inspect', 'check', 'query', 'run')) {
  Write-Error "unknown command '$Command'"
  exit 2
}
$SourceFile = $null
if ($Command -ne 'describe') {
  if ($Arguments.Count -lt 2 -or $Arguments[1].StartsWith('-')) { Write-Error "usage: .\pep.ps1 $Command FILE [options]"; exit 2 }
  $SourceFile = $Arguments[1]
}
$opamCommand = Get-Command opam -ErrorAction SilentlyContinue
if (-not $opamCommand) { Write-Error 'opam was not found'; exit 2 }
$opamRoot = if ($env:PEPIN_OPAM_ROOT) { $env:PEPIN_OPAM_ROOT } else { (Join-Path $env:LOCALAPPDATA 'opam') }
$buildDir = Join-Path $PSScriptRoot '_build\ocaml'
[IO.Directory]::CreateDirectory($buildDir) | Out-Null
$compilerSource = Join-Path $PSScriptRoot 'pep_ocaml.ml'
$compilerCopy = Join-Path $buildDir 'pep_ocaml.ml'
$compilerExe = Join-Path $buildDir 'pep.exe'
$sourceHash = (Get-FileHash -LiteralPath $compilerSource -Algorithm SHA256).Hash
$copyHash = if (Test-Path -LiteralPath $compilerCopy) { (Get-FileHash -LiteralPath $compilerCopy -Algorithm SHA256).Hash } else { '' }
$sourceChanged = $sourceHash -ne $copyHash
if ($sourceChanged) { Copy-Item -LiteralPath $compilerSource -Destination $compilerCopy -Force }
if ($sourceChanged -or -not (Test-Path -LiteralPath $compilerExe)) {
  & $opamCommand.Source exec --root $opamRoot --switch pepin-5.5.2 -- ocamlopt -o $compilerExe $compilerCopy
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$Forward = @($Arguments)
if ($SourceFile) { $Forward[1] = (Resolve-Path -LiteralPath $SourceFile -ErrorAction Stop).Path }
& $compilerExe @Forward
exit $LASTEXITCODE
