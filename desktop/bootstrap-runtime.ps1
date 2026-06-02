param(
    [string]$InstallDir,
    [switch]$SkipRequirements
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if (-not $InstallDir) {
    $InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$LogPath = Join-Path $InstallDir "simple-signal-bootstrap.log"

function Write-Step {
    param([string]$Message)
    Write-Host "[Simple Signal Setup] $Message"
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Get-PythonVersion {
    param([string]$PythonExe)

    try {
        $versionText = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
        if ($LASTEXITCODE -ne 0 -or -not $versionText) {
            return $null
        }
        return [version]$versionText.Trim()
    } catch {
        return $null
    }
}

function Test-SupportedPython {
    param([string]$PythonExe)

    $version = Get-PythonVersion -PythonExe $PythonExe
    if (-not $version) {
        return $false
    }

    return $version.Major -eq 3 -and $version.Minor -ge 8 -and $version.Minor -le 12
}

function Find-Python {
    $candidates = New-Object System.Collections.Generic.List[string]

    if ($env:LOCALAPPDATA) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"))
        $candidates.Add((Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"))
        $candidates.Add((Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"))
    }

    foreach ($command in @("python", "python3")) {
        $resolved = Get-Command $command -ErrorAction SilentlyContinue
        if ($resolved) {
            $candidates.Add($resolved.Source)
        }
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate) -and (Test-SupportedPython -PythonExe $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $exe = & $pyLauncher.Source -3.11 -c "import sys; print(sys.executable)"
            if ($LASTEXITCODE -eq 0 -and $exe -and (Test-SupportedPython -PythonExe $exe.Trim())) {
                return $exe.Trim()
            }
        } catch {
        }

        try {
            $exe = & $pyLauncher.Source -3 -c "import sys; print(sys.executable)"
            if ($LASTEXITCODE -eq 0 -and $exe -and (Test-SupportedPython -PythonExe $exe.Trim())) {
                return $exe.Trim()
            }
        } catch {
        }
    }

    return $null
}

function Add-ToUserPath {
    param([string]$PathToAdd)

    if (-not $PathToAdd -or -not (Test-Path -LiteralPath $PathToAdd)) {
        return
    }

    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not $current) {
        $current = ""
    }

    $parts = $current -split ";" | Where-Object { $_ }
    foreach ($part in $parts) {
        if ($part.TrimEnd("\") -ieq $PathToAdd.TrimEnd("\")) {
            return
        }
    }

    $newPath = if ($current) { "$PathToAdd;$current" } else { $PathToAdd }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$PathToAdd;$env:Path"
}

function Install-Python {
    $version = "3.11.9"
    $installerUrl = "https://www.python.org/ftp/python/$version/python-$version-amd64.exe"
    $installerPath = Join-Path $env:TEMP "python-$version-amd64.exe"

    Write-Step "Python was not found. Downloading Python $version..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $client = New-Object System.Net.WebClient
    $client.DownloadFile($installerUrl, $installerPath)

    Write-Step "Installing Python $version for the current user..."
    $arguments = @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_pip=1",
        "Include_launcher=1",
        "Include_test=0",
        "Shortcuts=0",
        "SimpleInstall=1"
    )

    $process = Start-Process -FilePath $installerPath -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) {
        throw "Python installer failed with exit code $($process.ExitCode)."
    }

    $python = Find-Python
    if (-not $python) {
        throw "Python installation finished, but python.exe could not be found."
    }

    return $python
}

function Ensure-Pip {
    param([string]$PythonExe)

    Write-Step "Checking pip..."
    & $PythonExe -m pip --version | Out-Host
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Step "pip was not found. Trying ensurepip..."
    & $PythonExe -m ensurepip --upgrade | Out-Host
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Step "ensurepip failed. Downloading get-pip.py..."
    $getPipPath = Join-Path $env:TEMP "get-pip.py"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $client = New-Object System.Net.WebClient
    $client.DownloadFile("https://bootstrap.pypa.io/get-pip.py", $getPipPath)
    Invoke-Native -FilePath $PythonExe -Arguments @($getPipPath)
}

try {
    Start-Transcript -Path $LogPath -Append | Out-Null

    Write-Step "Install directory: $InstallDir"
    $python = Find-Python
    if (-not $python) {
        $python = Install-Python
    }

    Write-Step "Using Python: $python"
    $pythonDir = Split-Path -Parent $python
    Add-ToUserPath -PathToAdd $pythonDir
    Add-ToUserPath -PathToAdd (Join-Path $pythonDir "Scripts")

    Ensure-Pip -PythonExe $python

    if (-not $SkipRequirements) {
        $requirements = Join-Path $InstallDir "resources\app-backend\requirements.txt"
        if (-not (Test-Path -LiteralPath $requirements)) {
            throw "requirements.txt not found: $requirements"
        }

        Write-Step "Upgrading pip, setuptools, and wheel..."
        Invoke-Native -FilePath $python -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")

        Write-Step "Installing Simple Signal requirements..."
        Invoke-Native -FilePath $python -Arguments @("-m", "pip", "install", "--upgrade", "-r", $requirements)
    } else {
        Write-Step "Skipping requirements install because -SkipRequirements was provided."
    }

    Write-Step "Runtime setup completed."
    exit 0
} catch {
    Write-Host "[Simple Signal Setup] ERROR: $($_.Exception.Message)"
    exit 1
} finally {
    try {
        Stop-Transcript | Out-Null
    } catch {
    }
}
