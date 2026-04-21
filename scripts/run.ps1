param(
    [switch]$SeedDemo
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend "venv\Scripts\python.exe"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [scriptblock]$Command,
        [string]$Name
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Ensure-FileFromExample($Target, $Example) {
    if (-not (Test-Path $Target) -and (Test-Path $Example)) {
        Copy-Item -LiteralPath $Example -Destination $Target
        Write-Host "Created $Target"
    }
}

function Test-PythonExecutable($PythonExe) {
    if (-not (Test-Path $PythonExe)) {
        return $false
    }
    try {
        & $PythonExe -c "import sys; print(sys.executable)" | Out-Host
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Find-SystemPython {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $out = & py -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out -and (Test-Path $out[0])) {
                return $out[0]
            }
        } catch {}
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        try {
            & $python.Source -c "import sys; print(sys.version)" | Out-Null
            if ($LASTEXITCODE -eq 0) {
                return $python.Source
            }
        } catch {}
    }

    return $null
}

function Test-BackendDependencies {
    try {
        & $Python -c "import django, rest_framework, rest_framework_simplejwt, corsheaders, dotenv, dj_database_url, pymysql, PIL, openpyxl, reportlab, requests, httpx, apscheduler, pytz; print('backend dependencies ready')" | Out-Host
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

Write-Step "Checking environment files"
Ensure-FileFromExample (Join-Path $Backend ".env") (Join-Path $Backend ".env.example")
Ensure-FileFromExample (Join-Path $Frontend ".env") (Join-Path $Frontend ".env.example")

Write-Step "Checking Python virtual environment"
if (-not (Test-PythonExecutable $Python)) {
    Write-Host "Existing backend venv is missing or not portable on this computer. Recreating it..." -ForegroundColor Yellow
    $SystemPython = Find-SystemPython
    if (-not $SystemPython) {
        throw "Python was not found. Please install Python 3.12 or newer, then run run.bat again."
    }

    $VenvDir = Join-Path $Backend "venv"
    if (Test-Path $VenvDir) {
        $Backup = Join-Path $Backend ("venv-broken-" + (Get-Date -Format "yyyyMMddHHmmss"))
        Move-Item -LiteralPath $VenvDir -Destination $Backup
        Write-Host "Moved invalid venv to $Backup"
    }

    Invoke-Checked { & $SystemPython -m venv $VenvDir } "Create backend venv"
    if (-not (Test-PythonExecutable $Python)) {
        throw "Created backend venv, but its Python executable still cannot run."
    }
}

Write-Step "Checking backend dependencies"
Push-Location $Backend
if (Test-BackendDependencies) {
    Write-Host "Backend dependencies already available. Skipping pip install."
} else {
    Write-Host "Backend dependencies are incomplete. Installing from requirements.txt..." -ForegroundColor Yellow
    Invoke-Checked { & $Python -m pip install --only-binary=:all: -r requirements.txt } "Install backend dependencies"
}

Write-Step "Applying database migrations"
Invoke-Checked { & $Python manage.py migrate } "Django migrate"

Write-Step "Ensuring admin account"
Invoke-Checked { & $Python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u,created=U.objects.get_or_create(username='admin', defaults={'role':'admin','is_staff':True,'is_superuser':True,'email':'admin@sleep-system.example'}); u.role='admin'; u.is_staff=True; u.is_superuser=True; u.set_password('admin123'); u.save(); print('admin/admin123 ready')" } "Ensure admin account"

if ($SeedDemo) {
    Write-Step "Seeding demo data"
    Invoke-Checked { & $Python manage.py seed_demo_data --yes } "Seed demo data"
}
Pop-Location

Write-Step "Checking frontend dependencies"
Push-Location $Frontend
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Invoke-Checked { & npm.cmd install } "Install frontend dependencies"
}
Pop-Location

Write-Step "Starting backend and frontend"
$BackendCmd = "cd /d `"$Backend`" && `"$Python`" manage.py runserver 127.0.0.1:8000"
$FrontendCmd = "cd /d `"$Frontend`" && npm.cmd run dev -- --host 127.0.0.1"

Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $BackendCmd -WindowStyle Normal
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $FrontendCmd -WindowStyle Normal

Write-Host ""
Write-Host "Sleep System is starting." -ForegroundColor Green
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Backend : http://127.0.0.1:8000/api/healthz/"
Write-Host "Admin   : admin / admin123"
Write-Host ""
Write-Host "Tip: run .\run.bat -SeedDemo to generate demo data before startup."
