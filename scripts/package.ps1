param(
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [switch]$IncludeVenv,
    [switch]$IncludeNodeModules
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$ReleaseRoot = Join-Path $Root "release"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$PackageName = "sleep-system-$Stamp"
$PackageDir = Join-Path $ReleaseRoot $PackageName
$ZipPath = "$PackageDir.zip"
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

function Copy-Filtered($Source, $Destination, [string[]]$SkipDirs, [string[]]$SkipFiles) {
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        if ($_.PSIsContainer) {
            if ($SkipDirs -contains $_.Name) { return }
            Copy-Filtered $_.FullName (Join-Path $Destination $_.Name) $SkipDirs $SkipFiles
        } else {
            if ($SkipFiles -contains $_.Name) { return }
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $Destination $_.Name)
        }
    }
}

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null

if (-not $SkipTests) {
    Write-Step "Running backend checks and score-engine tests"
    Push-Location $Backend
    Invoke-Checked { & $Python manage.py check } "Django check"
    Invoke-Checked { & $Python -m pytest tests\test_score_engine.py } "Score engine tests"
    Pop-Location
}

if (-not $SkipBuild) {
    Write-Step "Building frontend"
    Push-Location $Frontend
    Invoke-Checked { & npm.cmd run build } "Frontend build"
    Pop-Location
}

Write-Step "Collecting project files"
$backendSkipDirs = @("__pycache__", ".pytest_cache")
if (-not $IncludeVenv) { $backendSkipDirs += "venv" }
$backendSkipFiles = @(".env", "runserver.err.log", "runserver.out.log")

$frontendSkipDirs = @(".vscode")
if (-not $IncludeNodeModules) { $frontendSkipDirs += "node_modules" }
$frontendSkipFiles = @(".env", "vite.err.log", "vite.out.log")

Copy-Filtered $Backend (Join-Path $PackageDir "backend") $backendSkipDirs $backendSkipFiles
Copy-Filtered $Frontend (Join-Path $PackageDir "frontend") $frontendSkipDirs $frontendSkipFiles
Copy-Filtered (Join-Path $Root "docs") (Join-Path $PackageDir "docs") @() @()
Copy-Filtered (Join-Path $Root "scripts") (Join-Path $PackageDir "scripts") @() @()
Copy-Item -LiteralPath (Join-Path $Root "run.bat") -Destination (Join-Path $PackageDir "run.bat")
Copy-Item -LiteralPath (Join-Path $Root "package.bat") -Destination (Join-Path $PackageDir "package.bat")

Write-Step "Writing package README"
@"
# 学生睡眠管理系统交付包

## 一键运行

双击 `run.bat`，或在 PowerShell 中执行：

```powershell
.\run.bat
```

如需生成演示数据：

```powershell
.\run.bat -SeedDemo
```

默认地址：

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:8000/api/healthz/
- 管理员：admin / admin123

说明：`backend/venv` 是 Windows Python 虚拟环境，内部会记录创建它的本机 Python 路径。复制到另一台电脑后如果虚拟环境不可用，`run.bat` 会自动移动失效目录并重新创建 `backend/venv`。如果完整包中的依赖已经可用，脚本会跳过 `pip install`，避免重复下载或编译 Pillow 等包。目标电脑建议安装 Python 3.12 或更新版本、Node.js LTS。

## 目录

- `backend/`：Django 后端
- `frontend/`：Vue 3 前端
- `docs/`：论文、API、部署和实现对照材料
- `scripts/`：一键运行和打包脚本
"@ | Set-Content -LiteralPath (Join-Path $PackageDir "README.md") -Encoding UTF8

Write-Step "Compressing zip package"
Compress-Archive -LiteralPath $PackageDir -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Package created:" -ForegroundColor Green
Write-Host $ZipPath
