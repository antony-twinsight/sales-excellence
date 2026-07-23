param(
    [switch]$SkipInstall,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$LogDir = Join-Path $Root "logs"
$BackendLog = Join-Path $LogDir "backend.log"
$BackendErr = Join-Path $LogDir "backend.err.log"
$FrontendLog = Join-Path $LogDir "frontend.log"
$FrontendErr = Join-Path $LogDir "frontend.err.log"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Assert-PortFree {
    param([int]$Port)
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        throw "Port $Port is already in use by process $($listener.OwningProcess). Stop that process or choose another port."
    }
}

function Test-PortFree {
    param([int]$Port)
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    return $null -eq $listener
}

function Get-FreePort {
    param([int]$PreferredPort)

    $port = $PreferredPort
    while (-not (Test-PortFree $port)) {
        $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        Write-Step "Port $port is already in use by process $($listener.OwningProcess); trying $($port + 1)"
        $port += 1
    }

    return $port
}

function Copy-EnvIfMissing {
    param(
        [string]$Directory,
        [string]$TargetName
    )

    $source = Join-Path $Directory ".env.example"
    $target = Join-Path $Directory $TargetName
    if ((Test-Path $source) -and -not (Test-Path $target)) {
        Copy-Item $source $target
        Write-Step "Created $target"
    }
}

function Set-EnvValue {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $line = "$Name=$Value"
    if (-not (Test-Path $Path)) {
        Set-Content -Path $Path -Value $line
        return
    }

    $content = Get-Content -Path $Path
    $pattern = "^$([regex]::Escape($Name))="
    if ($content | Where-Object { $_ -match $pattern }) {
        $content = $content | ForEach-Object {
            if ($_ -match $pattern) { $line } else { $_ }
        }
    }
    else {
        $content += $line
    }

    Set-Content -Path $Path -Value $content
}

function Stop-ProcessTree {
    param([System.Diagnostics.Process]$Process)
    if ($Process -and -not $Process.HasExited) {
        taskkill /PID $Process.Id /T /F | Out-Null
    }
}

if (-not (Test-Path $BackendDir)) {
    throw "Backend folder not found: $BackendDir"
}

if (-not (Test-Path $FrontendDir)) {
    throw "Frontend folder not found: $FrontendDir"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Assert-Command "python"
Assert-Command "npm"

Copy-EnvIfMissing $BackendDir ".env"
Copy-EnvIfMissing $FrontendDir ".env.local"

$BackendPort = Get-FreePort $BackendPort
$FrontendPort = Get-FreePort $FrontendPort

$FrontendEnv = Join-Path $FrontendDir ".env.local"
Set-EnvValue $FrontendEnv "NEXT_PUBLIC_API_URL" "http://localhost:$BackendPort"

if (-not $SkipInstall) {
    $venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating backend virtual environment"
        Push-Location $BackendDir
        python -m venv .venv
        Pop-Location
    }

    Write-Step "Installing backend dependencies"
    Push-Location $BackendDir
    & $venvPython -m pip install -r requirements.txt
    Pop-Location

    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Step "Installing frontend dependencies"
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }
}

$backendPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $backendPython)) {
    $backendPython = "python"
}

Write-Step "Applying backend database migrations"
Push-Location $BackendDir
try {
    & $backendPython -m alembic upgrade head
}
finally {
    Pop-Location
}

Write-Step "Starting backend on http://localhost:$BackendPort"
$backendProcess = Start-Process `
    -FilePath $backendPython `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--reload-exclude", ".venv\*", "--host", "127.0.0.1", "--port", "$BackendPort") `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $BackendLog `
    -RedirectStandardError $BackendErr `
    -WindowStyle Hidden `
    -PassThru

Write-Step "Starting frontend on http://localhost:$FrontendPort"
$frontendProcess = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--port", "$FrontendPort") `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $FrontendLog `
    -RedirectStandardError $FrontendErr `
    -WindowStyle Hidden `
    -PassThru

try {
    Start-Sleep -Seconds 4
    Write-Host ""
    Write-Host "Sales Excellence Platform is starting." -ForegroundColor Green
    Write-Host "Frontend: http://localhost:$FrontendPort"
    Write-Host "Backend:  http://localhost:$BackendPort"
    Write-Host "Health:   http://localhost:$BackendPort/health"
    Write-Host ""
    Write-Host "Logs:"
    Write-Host "  $BackendLog"
    Write-Host "  $BackendErr"
    Write-Host "  $FrontendLog"
    Write-Host "  $FrontendErr"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop both servers."

    while ($true) {
        Start-Sleep -Seconds 2
        if ($backendProcess.HasExited) {
            throw "Backend process exited. Check $BackendErr"
        }
        if ($frontendProcess.HasExited) {
            throw "Frontend process exited. Check $FrontendErr"
        }
    }
}
finally {
    Write-Host ""
    Write-Step "Stopping app processes"
    Stop-ProcessTree $frontendProcess
    Stop-ProcessTree $backendProcess
}
