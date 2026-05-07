param(
    [switch]$RemoveVolumes
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$stateFile = Join-Path $repoRoot '.run\start-state.json'

function Stop-ProcessTreeById {
    param([int]$Id)

    try {
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$Id" -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty ProcessId
        foreach ($child in @($children)) {
            if ($null -ne $child) {
                [void](Stop-ProcessTreeById -Id $child)
            }
        }

        $taskkillOutput = & taskkill /PID $Id /T /F 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }

        $cimProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$Id" -ErrorAction SilentlyContinue
        if ($null -ne $cimProcess) {
            $result = Invoke-CimMethod -InputObject $cimProcess -MethodName Terminate -ErrorAction SilentlyContinue
            if ($null -ne $result -and $result.ReturnValue -eq 0) {
                return $true
            }
        }

        if ($taskkillOutput) {
            Write-Host ($taskkillOutput -join [Environment]::NewLine)
        }
        return $false
    } catch {
        return $false
    }
}

function Stop-LocalProcesses {
    if (-not (Test-Path -LiteralPath $stateFile)) {
        Write-Host 'No local start state found. Trying to clear common ports.'
        foreach ($port in 8000, 5173) {
            $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($listener in $listeners) {
                if ($null -ne $listener) {
                    if (Stop-ProcessTreeById -Id $listener) {
                        Write-Host ("Cleared port {0} (PID {1})" -f $port, $listener)
                    } else {
                        Write-Host ("Could not clear port {0} (PID {1})" -f $port, $listener)
                    }
                }
            }
        }
        return
    }

    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    foreach ($proc in @($state.processes)) {
        if ($null -ne $proc.pid) {
            if (Stop-ProcessTreeById -Id $proc.pid) {
                Write-Host ("Stopped {0} (PID {1})" -f $proc.name, $proc.pid)
            } else {
                Write-Host ("Skipping {0} (PID {1})" -f $proc.name, $proc.pid)
            }
        }
    }

    Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
}

if (Test-Path -LiteralPath $stateFile) {
    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    if ($state.mode -eq 'local') {
        Stop-LocalProcesses
    } elseif (Get-Command docker -ErrorAction SilentlyContinue) {
        $composeArgs = @('compose', 'down')
        if ($RemoveVolumes) {
            $composeArgs += '--volumes'
        }

        Write-Host ('Running: docker ' + ($composeArgs -join ' '))
        docker @composeArgs
        Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host 'The last start was docker mode, but Docker is not available now.'
    }
} elseif (Get-Command docker -ErrorAction SilentlyContinue) {
    $composeArgs = @('compose', 'down')
    if ($RemoveVolumes) {
        $composeArgs += '--volumes'
    }

    Write-Host ('Running: docker ' + ($composeArgs -join ' '))
    docker @composeArgs
    Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
} else {
    Stop-LocalProcesses
}

Write-Host ''
Write-Host 'Stopped Auto Test Platform.'
Write-Host 'Use .\start-all.ps1 to start it again.'
