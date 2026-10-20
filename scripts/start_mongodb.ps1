$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$localServer = Join-Path $root ".local\mongodb\bin\mongod.exe"
$server = Get-Command mongod -ErrorAction SilentlyContinue
if (Test-Path $localServer) {
    $executable = $localServer
} elseif ($server) {
    $executable = $server.Source
} else {
    throw "MongoDB server not found. Install MongoDB Community and add its bin directory to PATH, or put mongod.exe in .local\mongodb\bin."
}
$data = Join-Path $root ".local\mongodb\data"
New-Item -ItemType Directory -Force -Path $data | Out-Null
Write-Host "Starting MongoDB on 127.0.0.1:27017. Keep this terminal open."
& $executable --dbpath $data --bind_ip 127.0.0.1 --port 27017
if ($LASTEXITCODE -ne 0) { throw "MongoDB exited with code $LASTEXITCODE. Check the output above." }
