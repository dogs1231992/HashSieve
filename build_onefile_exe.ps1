$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$AppName = "HashSieve"
$Venv = Join-Path $PSScriptRoot ".build_venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$Release = Join-Path $PSScriptRoot "release"

function Resolve-BasePython {
    # Prefer Python Launcher when it exists, but also support Conda/normal Python.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3 --version | Out-Null
            return @{ Exe = "py"; Args = @("-3") }
        } catch {
            # Keep trying other Python commands below.
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            & python --version | Out-Null
            return @{ Exe = "python"; Args = @() }
        } catch {
            # Keep trying python3 below.
        }
    }

    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        try {
            & python3 --version | Out-Null
            return @{ Exe = "python3"; Args = @() }
        } catch {
            # No usable Python command found.
        }
    }

    throw "Python was not found. Please install Python 3.10+ or run this script from Anaconda/Miniconda Prompt, then try again."
}

Write-Host "== $AppName one-file EXE build =="

if (!(Test-Path $Python)) {
    $BasePython = Resolve-BasePython
    Write-Host "Creating build virtual environment with: $($BasePython.Exe) $($BasePython.Args -join ' ')"
    & $BasePython.Exe @($BasePython.Args) -m venv $Venv
}

if (!(Test-Path $Python)) {
    throw "Build virtual environment was not created correctly: $Python"
}

Write-Host "Using Python: $Python"
& $Python --version

& $Python -m pip install --upgrade pip
& $Python -m pip install --prefer-binary -r requirements.txt

if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (!(Test-Path $Release)) { New-Item -ItemType Directory -Path $Release | Out-Null }

Write-Host "Running PyInstaller..."
& $Python -m PyInstaller --clean --noconfirm HashSieve.spec

$ExeSource = Join-Path $PSScriptRoot "dist\HashSieve.exe"
$ExeDest = Join-Path $Release "HashSieve.exe"

if (!(Test-Path $ExeSource)) {
    throw "PyInstaller finished, but the expected EXE was not found: $ExeSource"
}

Copy-Item $ExeSource $ExeDest -Force

Write-Host "Writing checksums..."
$sha256 = (Get-FileHash $ExeDest -Algorithm SHA256).Hash.ToLower()
$sha512 = (Get-FileHash $ExeDest -Algorithm SHA512).Hash.ToLower()
Set-Content -Path (Join-Path $Release "HashSieve.exe.sha256") -Value "$sha256  HashSieve.exe" -Encoding ASCII
Set-Content -Path (Join-Path $Release "HashSieve.exe.sha512") -Value "$sha512  HashSieve.exe" -Encoding ASCII
Set-Content -Path (Join-Path $Release "CHECKSUMS.txt") -Value @("SHA256  $sha256  HashSieve.exe", "SHA512  $sha512  HashSieve.exe") -Encoding ASCII

Write-Host "Cleaning intermediate build files..."
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path $Venv) { Remove-Item $Venv -Recurse -Force }
Get-ChildItem -Path $PSScriptRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Done: $ExeDest"
