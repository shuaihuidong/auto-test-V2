param(
    [ValidateSet('auto', 'docker', 'local')]
    [string]$Mode = 'auto',
    [switch]$Build,
    [switch]$Detach = $true,
    [string[]]$Profiles
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$stateDir = Join-Path $repoRoot '.run'
$stateFile = Join-Path $stateDir 'start-state.json'

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message =="
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Resolve-CommandPath {
    param([string]$Name)

    $cmd = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $cmd) {
        return $null
    }

    return $cmd.Source
}

function Save-State {
    param(
        [string]$LaunchMode,
        [object[]]$Processes
    )

    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
    $payload = [ordered]@{
        mode = $LaunchMode
        started_at = (Get-Date).ToString('o')
        processes = $Processes
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $stateFile
}

function Set-TempEnv {
    param(
        [string]$Name,
        [string]$Value
    )

    $previous = [System.Environment]::GetEnvironmentVariable($Name, 'Process')
    [System.Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
    return $previous
}

function Restore-TempEnv {
    param(
        [string]$Name,
        [string]$PreviousValue
    )

    [System.Environment]::SetEnvironmentVariable($Name, $PreviousValue, 'Process')
}

function Stop-ProcessTreeById {
    param([int]$Id)

    try {
        taskkill /PID $Id /T /F | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Clear-Port {
    param([int]$Port)

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($listener in $listeners) {
        if ($null -ne $listener) {
            $ok = Stop-ProcessTreeById -Id $listener
            if ($ok) {
                Write-Host ("Cleared port {0} (PID {1})" -f $Port, $listener)
            } else {
                Write-Host ("Could not clear port {0} (PID {1})" -f $Port, $listener)
            }
        }
    }
}

function Start-LocalBackend {
    $backendDir = Join-Path $repoRoot 'backend'
    $logDir = Join-Path $backendDir 'logs'
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    $envBackup = [ordered]@{}
    $envBackup.DJANGO_SETTINGS_MODULE = Set-TempEnv -Name 'DJANGO_SETTINGS_MODULE' -Value 'core.settings'
    $envBackup.DEBUG = Set-TempEnv -Name 'DEBUG' -Value 'True'
    $envBackup.DJANGO_ALLOWED_HOSTS = Set-TempEnv -Name 'DJANGO_ALLOWED_HOSTS' -Value 'localhost,127.0.0.1,127.0.0.1:5173,localhost:5173'
    $envBackup.CORS_ALLOWED_ORIGINS = Set-TempEnv -Name 'CORS_ALLOWED_ORIGINS' -Value 'http://localhost:5173,http://127.0.0.1:5173'
    $envBackup.CHANNEL_LAYER_BACKEND = Set-TempEnv -Name 'CHANNEL_LAYER_BACKEND' -Value 'inmemory'
    $envBackup.RABBITMQ_HOST = Set-TempEnv -Name 'RABBITMQ_HOST' -Value '127.0.0.1'
    $envBackup.DB_ENGINE = Set-TempEnv -Name 'DB_ENGINE' -Value 'sqlite3'
    $envBackup.DB_PATH = Set-TempEnv -Name 'DB_PATH' -Value (Join-Path $backendDir 'db\db.sqlite3')

    try {
        Clear-Port -Port 8000
        Clear-Port -Port 5173

        Write-Host 'Running backend migrations...'
        Push-Location $backendDir
        try {
            python manage.py migrate --noinput
        } finally {
            Pop-Location
        }

        $backendLog = Join-Path $logDir 'start-backend.log'
        $backendErr = Join-Path $logDir 'start-backend.err.log'

        if (-not (Test-Command 'python')) {
            throw 'Python is not installed or not available in PATH.'
        }

        $pythonPath = Resolve-CommandPath 'python'
        $backendArgs = @()
        & $pythonPath -c "import daphne" | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $backendArgs = @('-m', 'daphne', '-b', '0.0.0.0', '-p', '8000', 'core.asgi:application')
        } else {
            Write-Host 'Daphne is not available. Falling back to Django runserver.'
            $backendArgs = @('manage.py', 'runserver', '0.0.0.0:8000')
        }

        $backendProcess = Start-Process -FilePath $pythonPath -ArgumentList $backendArgs -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr

        $schedulerLog = Join-Path $logDir 'start-scheduler.log'
        $schedulerErr = Join-Path $logDir 'start-scheduler.err.log'
        $schedulerProcess = Start-Process -FilePath $pythonPath -ArgumentList @('manage.py', 'run_scheduler', '--interval', '30') -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $schedulerLog -RedirectStandardError $schedulerErr

        $frontendDir = Join-Path $repoRoot 'frontend'
        $frontendLog = Join-Path $frontendDir 'start-frontend.log'
        $frontendErr = Join-Path $frontendDir 'start-frontend.err.log'

        if (-not (Test-Command 'npm')) {
            throw 'Node.js/npm is not installed or not available in PATH.'
        }

        $npmCmd = Resolve-CommandPath 'npm.cmd'
        if ($null -eq $npmCmd) {
            throw 'npm.cmd was not found in PATH.'
        }

        if (-not (Test-Path -LiteralPath (Join-Path $frontendDir 'node_modules'))) {
            Write-Host 'Installing frontend dependencies...'
            Push-Location $frontendDir
            try {
                & $npmCmd install
            } finally {
                Pop-Location
            }
        }

        $frontendArgs = @('run', 'dev', '--', '--host', '0.0.0.0')
        $frontendProcess = Start-Process -FilePath $npmCmd -ArgumentList $frontendArgs -WorkingDirectory $frontendDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr

        Save-State -LaunchMode 'local' -Processes @(
            [ordered]@{ name = 'backend'; pid = $backendProcess.Id; command = 'python -m daphne'; log = $backendLog },
            [ordered]@{ name = 'scheduler'; pid = $schedulerProcess.Id; command = 'python manage.py run_scheduler --interval 30'; log = $schedulerLog },
            [ordered]@{ name = 'frontend'; pid = $frontendProcess.Id; command = 'npm run dev'; log = $frontendLog }
        )
    } finally {
        foreach ($entry in $envBackup.GetEnumerator()) {
            Restore-TempEnv -Name $entry.Key -PreviousValue $entry.Value
        }
    }

    Write-Section 'Service URLs'
    Write-Host 'Frontend:  http://localhost:5173'
    Write-Host 'Backend:   http://localhost:8000/api/'
    Write-Host 'Admin:     http://localhost:8000/admin/'
    Write-Host 'Logs:      backend/logs/start-backend.log'
    Write-Host '           backend/logs/start-scheduler.log'
    Write-Host '           frontend/start-frontend.log'
}

function Start-DockerMode {
    $composeArgs = @('compose', 'up')
    if ($Detach) {
        $composeArgs += '-d'
    }
    if ($Build) {
        $composeArgs += '--build'
    }
    foreach ($profile in $Profiles) {
        $composeArgs += @('--profile', $profile)
    }

    Write-Host ('Running: docker ' + ($composeArgs -join ' '))
    docker @composeArgs
    Save-State -LaunchMode 'docker' -Processes @()

    Write-Section 'Service URLs'
    Write-Host 'Frontend:  http://localhost'
    Write-Host 'Backend:   http://localhost:8000/api/'
    Write-Host 'Admin:     http://localhost:8000/admin/'
    Write-Host 'RabbitMQ:  http://localhost:15672/'
    Write-Host 'Redis:     localhost:6379'
    if ($Profiles -contains 'postgres') {
        Write-Host 'Postgres:  localhost:5432'
    }
    if ($Profiles -contains 'minio') {
        Write-Host 'MinIO:     http://localhost:9001/'
    }
}

Write-Section 'Starting Auto Test Platform'

$dockerAvailable = Test-Command 'docker'
$launchMode = $Mode
if ($launchMode -eq 'auto') {
    $launchMode = if ($dockerAvailable) { 'docker' } else { 'local' }
}

if ($launchMode -eq 'docker' -and -not $dockerAvailable) {
    Write-Host 'Docker was requested, but it is not available. Falling back to local mode.'
    $launchMode = 'local'
}

if ($launchMode -eq 'docker') {
    Start-DockerMode
} else {
    Start-LocalBackend
}

Write-Section 'Useful Commands'
Write-Host 'Stop all:   .\stop-all.ps1'
Write-Host 'Mode auto:  .\start-all.ps1'
Write-Host 'Docker:     .\start-all.ps1 -Mode docker'
Write-Host 'Local:      .\start-all.ps1 -Mode local'
Write-Host 'Rebuild:    .\start-all.ps1 -Build -Mode docker'
