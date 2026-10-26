param(
    [ValidateSet('all', 'clang', 'gcc')]
    [string] $Compiler = 'all',
    [switch] $Probe,
    [switch] $Discover,
    [switch] $Sanitize
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $root '..\..')
$buildRoot = Join-Path $repoRoot '_build\c23-feasibility'
New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
$manifestPath = Join-Path $root 'toolchain_paths.json'
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json

function Expand-C23Candidate([string] $candidate) {
    $expanded = $candidate
    foreach ($match in [regex]::Matches($candidate, '\$\{([^}]+)\}')) {
        $value = [Environment]::GetEnvironmentVariable($match.Groups[1].Value)
        if ($null -eq $value) { return $null }
        $expanded = $expanded.Replace($match.Value, $value)
    }
    return [Environment]::ExpandEnvironmentVariables($expanded)
}

function Resolve-C23Compiler([string] $name) {
    $override = if ($name -eq 'clang') { $env:PEP_C23_CLANG } else { $env:PEP_C23_GCC }
    if ($override -and (Test-Path -LiteralPath $override)) { return (Resolve-Path -LiteralPath $override).Path }
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $known = @($manifest.$name)
    foreach ($rawCandidate in $known) {
        $candidate = Expand-C23Candidate $rawCandidate
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    return $null
}

function Resolve-C23AsanRuntime([string] $compilerPath) {
    $resource = (& $compilerPath '--print-resource-dir' 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -eq 0 -and $resource) {
        $candidate = Join-Path ([string]$resource).Trim() 'lib\windows'
        if (Test-Path -LiteralPath (Join-Path $candidate 'clang_rt.asan_dynamic-x86_64.dll')) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    $compilerRoot = Split-Path (Split-Path $compilerPath -Parent) -Parent
    $clangRoot = Join-Path $compilerRoot 'lib\clang'
    if (Test-Path -LiteralPath $clangRoot) {
        foreach ($version in Get-ChildItem -LiteralPath $clangRoot -Directory | Sort-Object Name -Descending) {
            $candidate = Join-Path $version.FullName 'lib\windows'
            if (Test-Path -LiteralPath (Join-Path $candidate 'clang_rt.asan_dynamic-x86_64.dll')) { return $candidate }
        }
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
    if ($Discover) { continue }
    $outDir = Join-Path $buildRoot $name
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $flags = @('-std=c23', '-Wall', '-Wextra', '-Wpedantic', '-Werror', '-O2', '-I', $root)
    if ($Sanitize) { $flags += @('-fsanitize=address') }
    $runtime = Join-Path $root 'c23_runtime.c'
    $probeSource = if ($Probe) { Join-Path $root 'c23_language_probe.c' } else { Join-Path $root 'c23_probe.c' }
    $outputName = if ($Probe) { 'pep_c23_language_probe' } else { 'pep_c23_probe' }
    if ($Sanitize) { $outDir = Join-Path $outDir 'sanitize'; New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
    $output = Join-Path $outDir $(if ($IsWindows) { "$outputName.exe" } else { $outputName })
    Write-Output "COMMAND|$path $($flags -join ' ') $runtime $probeSource -o $output"
    & $path @flags $runtime $probeSource '-o' $output
    if ($LASTEXITCODE -ne 0) { throw "$name failed strict C23 compilation" }
    Write-Output "BUILT|$name|$output"
    if ($Sanitize -and $name -eq 'clang') {
        $asanRuntime = Resolve-C23AsanRuntime $path
        if ($asanRuntime) { Write-Output "SANITIZER_RUNTIME|$asanRuntime" }
        else { Write-Output "SANITIZER_RUNTIME|unavailable" }
    }
}

if ($missing.Count -gt 0) {
    exit 2
}
