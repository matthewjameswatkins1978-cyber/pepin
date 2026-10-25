param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $Arguments
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if ($Arguments.Count -eq 0) {
  Write-Error 'usage: .\pep.ps1 check|build|run FILE | describe --json'
  exit 2
}
$command = $Arguments[0]
$moonCommand = Get-Command moon -ErrorAction SilentlyContinue
if ($moonCommand) {
  $moon = $moonCommand.Source
  $moonBin = Split-Path -Parent $moon
} else {
  $moon = Join-Path $env:USERPROFILE '.moon\bin\moon.exe'
  $moonBin = Split-Path -Parent $moon
}
if (-not (Test-Path -LiteralPath $moon)) {
  Write-Error 'MoonBit was not found. Install it or set PATH to the MoonBit bin directory.'
  exit 2
}

$buildOutput = & $moon -C $root build --target native 2>&1
if ($LASTEXITCODE -ne 0) { $buildOutput | ForEach-Object { [Console]::Error.WriteLine($_) }; exit $LASTEXITCODE }
$seed = Join-Path $root '_build\native\debug\build\cmd\main\main.exe'
if (-not (Test-Path -LiteralPath $seed)) {
  Write-Error "MoonBit build did not produce the expected seed executable: $seed"
  exit 2
}

if ($command -eq 'describe') {
  & $seed describe --json
  exit $LASTEXITCODE
}
if ($command -notin @('check', 'build', 'run')) {
  Write-Error "unknown command '$command'; expected check, build, run, or describe"
  exit 2
}
$sourceArgument = $Arguments | Where-Object { $_ -ne $command -and $_ -ne '--json' } | Select-Object -First 1
$json = $Arguments -contains '--json'
if (-not $sourceArgument) {
  Write-Error "usage: .\pep.ps1 $command FILE"
  exit 2
}
try {
  $sourcePath = (Resolve-Path -LiteralPath $sourceArgument -ErrorAction Stop).Path
  $source = [System.IO.File]::ReadAllText($sourcePath, [System.Text.UTF8Encoding]::new($false, $true))
} catch {
  if ($json) {
    [Console]::Out.WriteLine('{"schemaVersion":1,"diagnostics":[{"code":"PEPCLI001","severity":"error","message":"Could not read source file","file":' + (@($sourceArgument | ConvertTo-Json -Compress)) + ',"line":1,"column":1}]}')
  } else {
    [Console]::Error.WriteLine("$sourceArgument`:1:1: error[PEPCLI001]: Could not read source file")
  }
  exit 1
}

$compilerCommand = if ($command -eq 'build' -or $command -eq 'run') { 'emit-c' } else { 'check' }
$seedArguments = @($compilerCommand, $sourcePath)
if ($json) { $seedArguments += '--json' }
$psi = [System.Diagnostics.ProcessStartInfo]::new($seed)
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.StandardInputEncoding = [System.Text.UTF8Encoding]::new($false)
$psi.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
$psi.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
foreach ($arg in $seedArguments) { [void]$psi.ArgumentList.Add($arg) }
$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $psi
[void]$process.Start()
$process.StandardInput.Write($source)
$process.StandardInput.Close()
$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
$process.WaitForExit()

$compilerOutput = $stdoutTask.GetAwaiter().GetResult()
$compilerError = $stderrTask.GetAwaiter().GetResult()
if ($process.ExitCode -ne 0) {
  if ($compilerOutput) { [Console]::Out.Write($compilerOutput) }
  if ($compilerError) { [Console]::Error.Write($compilerError) }
  exit $process.ExitCode
}
if ($command -eq 'check') {
  if ($compilerOutput) { [Console]::Out.Write($compilerOutput) }
  if ($compilerError) { [Console]::Error.Write($compilerError) }
  exit 0
}

$buildDirectory = Join-Path $root '_build\pep'
[System.IO.Directory]::CreateDirectory($buildDirectory) | Out-Null
$stem = [System.IO.Path]::GetFileNameWithoutExtension($sourcePath)
$cPath = Join-Path $buildDirectory "$stem.c"
$exePath = Join-Path $buildDirectory "$stem.exe"
[System.IO.File]::WriteAllText($cPath, $compilerOutput, [System.Text.UTF8Encoding]::new($false))
$tcc = Join-Path $moonBin 'internal\tcc.exe'
$moonRoot = Split-Path -Parent $moonBin
if (-not (Test-Path -LiteralPath $tcc)) {
  Write-Error "The bundled C compiler was not found: $tcc"
  exit 2
}
$runtime = Join-Path $root 'runtime\pep_runtime.c'
$include = Join-Path $root 'runtime'
& $tcc -std=c11 "-B$moonRoot" "-I$include" $cPath $runtime -o $exePath
if ($LASTEXITCODE -ne 0) {
  if ($json) {
    [Console]::Out.WriteLine('{"schemaVersion":1,"diagnostics":[{"code":"PEP5001","severity":"error","message":"Native C compilation failed","file":' + (@($sourceArgument | ConvertTo-Json -Compress)) + ',"line":1,"column":1}]}')
  }
  exit $LASTEXITCODE
}
if ($command -eq 'run') {
  & $exePath
  exit $LASTEXITCODE
}
Write-Output $exePath
