$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AppRoot = $PSScriptRoot
Set-Location $AppRoot

$pythonCommand = Get-Command python -ErrorAction Stop
$Python = $pythonCommand.Source

Write-Host "[1/5] Installing pinned project requirements..." -ForegroundColor Cyan
& $Python -m pip install --disable-pip-version-check -r (Join-Path $AppRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed (exit $LASTEXITCODE)." }

Write-Host "[2/5] Compiling application and tests..." -ForegroundColor Cyan
& $Python -B -m compileall -q app.py components config models pages services tests
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed (exit $LASTEXITCODE)." }

Write-Host "[3/5] Running the complete test suite, including Streamlit AppTest..." -ForegroundColor Cyan
& $Python -B -m pytest -q -p no:cacheprovider tests
if ($LASTEXITCODE -ne 0) { throw "The complete test suite failed (exit $LASTEXITCODE)." }

Write-Host "[4/5] Verifying package SHA-256 manifest..." -ForegroundColor Cyan
$manifestPath = Join-Path $ProjectRoot 'PACKAGE_SHA256_MANIFEST.txt'
if (-not (Test-Path $manifestPath)) { throw "Missing package manifest: $manifestPath" }
$manifestErrors = @()
foreach ($line in Get-Content $manifestPath) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $parts = $line -split '\s{2,}', 3
    if ($parts.Count -ne 3) { $manifestErrors += "Malformed manifest row: $line"; continue }
    $filePath = Join-Path $ProjectRoot $parts[2]
    if (-not (Test-Path $filePath -PathType Leaf)) { $manifestErrors += "Missing: $($parts[2])"; continue }
    $item = Get-Item $filePath
    $actualHash = (Get-FileHash $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $parts[0] -or $item.Length -ne [int64]$parts[1]) {
        $manifestErrors += "Hash/size mismatch: $($parts[2])"
    }
}
if ($manifestErrors.Count -gt 0) { throw ($manifestErrors -join "`n") }

Write-Host "[5/5] Starting Streamlit and checking HTTP health..." -ForegroundColor Cyan
$port = 8515
while ($true) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
    try { $listener.Start(); $listener.Stop(); break }
    catch { $port++; if ($port -gt 8550) { throw 'No free smoke-test port between 8515 and 8550.' } }
}
$logRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("superrr-selector-smoke-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$stdout = Join-Path $logRoot 'streamlit.stdout.log'
$stderr = Join-Path $logRoot 'streamlit.stderr.log'
$process = $null
try {
    $process = Start-Process -FilePath $Python -ArgumentList @(
        '-m', 'streamlit', 'run', 'app.py',
        '--server.port', "$port",
        '--server.headless', 'true'
    ) -WorkingDirectory $AppRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr

    $healthy = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($process.HasExited) { break }
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $healthy = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $healthy) {
        $outText = if (Test-Path $stdout) { Get-Content $stdout -Raw } else { '' }
        $errText = if (Test-Path $stderr) { Get-Content $stderr -Raw } else { '' }
        throw "Streamlit did not return HTTP 200.`nSTDOUT:`n$outText`nSTDERR:`n$errText"
    }
    Write-Host "Streamlit returned HTTP 200 on port $port." -ForegroundColor Green
}
finally {
    if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
}

Write-Host 'PASS: dependency install, compilation, full tests, package manifest and Streamlit HTTP smoke test.' -ForegroundColor Green
Write-Host 'Note: these checks do not grant production authorization or validate IPL player rankings.' -ForegroundColor Yellow
