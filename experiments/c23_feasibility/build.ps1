param(
    [ValidateSet('all', 'clang', 'gcc')]
    [string] $Compiler = 'all',
    [switch] $Probe
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $root '..\..')
$buildRoot = Join-Path $repoRoot '_build\c23-feasibility'
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null

function Resolve-C23Compiler([string] $name) {
    $override = if ($name -eq 'clang') { $env:PEP_C23_CLANG } else { $env:PEP_C23_GCC }
    if ($override -and (Test-Path -LiteralPath $override)) { return (Resolve-Path -LiteralPath $override).Path }
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $known = if ($name -eq 'clang') {
        @('C:\msys64\clang64\bin\clang.exe', 'C:\Program Files\LLVM\bin\clang.exe', 'C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Tools\Llvm\bin\clang.exe')
    } else {
        @('C:\msys64\clang64\bin\gcc.exe', 'C:\msys64\mingw64\bin\gcc.exe')
    }
    foreach ($candidate in $known) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

$requested = if ($Compiler -eq 'all') { @('clang', 'gcc') } else { @($Compiler) }
$missing = @()
foreach ($name in $requested) {
    $path = Resolve-C23Compiler $name
    if (-not $path) {
        Write-Output "UNAVAILABLE|$name"
        $missing += $name
        continue
    }
    $version = (& $path --version 2>&1 | Select-Object -First 1)
    Write-Output "FOUND|$name|$path|$version"
    $outDir = Join-Path $buildRoot $name
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $flags = @('-std=c23', '-Wall', '-Wextra', '-Wpedantic', '-Werror', '-O2', '-I', $root)
    $runtime = Join-Path $root 'c23_runtime.c'
    $probeSource = if ($Probe) { Join-Path $root 'c23_language_probe.c' } else { Join-Path $root 'c23_probe.c' }
    $output = Join-Path $outDir $(if ($IsWindows) { 'pep_c23_probe.exe' } else { 'pep_c23_probe' })
    & $path @flags $runtime $probeSource '-o' $output
    if ($LASTEXITCODE -ne 0) { throw "$name failed strict C23 compilation" }
    Write-Output "BUILT|$name|$output"
}

if ($missing.Count -gt 0) {
    exit 2
}
