[CmdletBinding()]
param(
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot = Split-Path -Parent $backendDir
$envPath = Join-Path $backendDir ".env"
$composePath = Join-Path $backendDir "docker-compose.yml"
if (-not (Test-Path -LiteralPath $envPath)) { throw "backend-news/.env tidak ditemukan." }

$settings = @{}
foreach ($line in [System.IO.File]::ReadAllLines($envPath)) {
    if ($line -match '^\s*([^#=\s]+)\s*=\s*(.*)\s*$') {
        $settings[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
    }
}
foreach ($key in @("POSTGRES_USER", "POSTGRES_DB")) {
    if ([string]::IsNullOrWhiteSpace($settings[$key])) { throw "$key belum diatur di backend-news/.env." }
}

$composeArgs = @("compose", "--env-file", $envPath, "--project-directory", $backendDir, "-f", $composePath)
$null = & docker info --format '{{.ServerVersion}}' 2>$null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine tidak dapat diakses. Pastikan Docker Desktop berjalan." }
$dbId = ((& docker @composeArgs ps -q db) -join "`n").Trim()
if ($LASTEXITCODE -ne 0 -or -not $dbId) { throw "Container database belum dibuat. Jalankan docker compose --env-file backend-news/.env -f backend-news/docker-compose.yml up -d db terlebih dahulu." }

$backupDir = Join-Path $backendDir "backups"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $backupDir ("news-docker-{0}.dump" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
} elseif (-not [System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath = Join-Path $repoRoot $OutputPath
}
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$remotePath = "/tmp/news-db-backup-$([guid]::NewGuid().ToString('N')).dump"

try {
    Write-Host "Membuat backup custom-format dari PostgreSQL Docker..."
    & docker @composeArgs exec -T db pg_dump --username $settings["POSTGRES_USER"] --dbname $settings["POSTGRES_DB"] `
        --format=custom --no-owner --no-acl --file $remotePath
    if ($LASTEXITCODE -ne 0) { throw "pg_dump di container gagal." }
    & docker @composeArgs cp "db:$remotePath" $OutputPath
    if ($LASTEXITCODE -ne 0) { throw "Gagal menyalin file backup dari container." }
} finally {
    & docker @composeArgs exec -T db rm -f $remotePath 2>$null | Out-Null
}

Write-Host "Backup tersimpan: $OutputPath"
