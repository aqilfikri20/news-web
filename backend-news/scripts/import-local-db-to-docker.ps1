[CmdletBinding()]
param(
    # Required only when the Docker target already has users or news.
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot = Split-Path -Parent $backendDir
$frontendDir = Join-Path $repoRoot "frontend-news"
$envPath = Join-Path $backendDir ".env"
$composePath = Join-Path $backendDir "docker-compose.yml"
$frontendComposePath = Join-Path $frontendDir "docker-compose.yml"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "File backend-news/.env tidak ditemukan. Buat dari backend-news/.env.example dan isi koneksi database."
}
if (-not (Test-Path -LiteralPath $composePath) -or -not (Test-Path -LiteralPath $frontendComposePath)) {
    throw "Compose file backend-news/docker-compose.yml atau frontend-news/docker-compose.yml tidak ditemukan."
}

$settings = @{}
foreach ($line in [System.IO.File]::ReadAllLines($envPath)) {
    if ($line -match '^\s*([^#=\s]+)\s*=\s*(.*)\s*$') {
        $settings[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
    }
}

foreach ($key in @("DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")) {
    if (-not $settings.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($settings[$key])) {
        throw "Konfigurasi $key belum tersedia di backend-news/.env."
    }
}

$sourceUrl = $settings["DATABASE_URL"] -replace '^postgresql\+[^:]+://', 'postgresql://'
try {
    $sourceUri = [System.Uri]$sourceUrl
    $userInfo = $sourceUri.UserInfo.Split(':', 2)
    if ($userInfo.Count -ne 2 -or -not $sourceUri.AbsolutePath.Trim('/')) {
        throw "DATABASE_URL tidak memuat username, password, host, dan nama database."
    }
    $sourceUser = [System.Uri]::UnescapeDataString($userInfo[0])
    $sourcePassword = [System.Uri]::UnescapeDataString($userInfo[1])
    $sourceDatabase = [System.Uri]::UnescapeDataString($sourceUri.AbsolutePath.Trim('/'))
    $sourcePort = if ($sourceUri.IsDefaultPort) { 5432 } else { $sourceUri.Port }
} catch {
    throw "DATABASE_URL tidak valid untuk koneksi database lama: $($_.Exception.Message)"
}

$pgDump = Get-Command "pg_dump" -ErrorAction SilentlyContinue
if (-not $pgDump) {
    $postgresProgramFiles = Join-Path $env:ProgramFiles "PostgreSQL"
    if (Test-Path -LiteralPath $postgresProgramFiles) {
        $pgDump = Get-ChildItem -LiteralPath $postgresProgramFiles -Filter "pg_dump.exe" -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
    }
}
if (-not $pgDump) {
    throw "pg_dump tidak ditemukan. Tambahkan folder PostgreSQL\bin ke PATH, lalu jalankan skrip ini lagi."
}
$pgDumpPath = if ($pgDump -is [System.IO.FileInfo]) { $pgDump.FullName } else { $pgDump.Source }
if ([string]::IsNullOrWhiteSpace($pgDumpPath)) {
    throw "Lokasi pg_dump tidak dapat ditentukan. Tambahkan folder PostgreSQL\bin ke PATH, lalu jalankan skrip ini lagi."
}

$null = & docker info --format '{{.ServerVersion}}' 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Engine belum dapat diakses. Pastikan Docker Desktop berjalan dan jalankan ulang skrip."
}

$composeArgs = @(
    "--env-file", $envPath,
    "--project-directory", $backendDir,
    "-f", $composePath
)
$frontendComposeArgs = @(
    "--env-file", $envPath,
    "--project-directory", $frontendDir,
    "-f", $frontendComposePath
)
function Invoke-Compose {
    param([Parameter(Mandatory)][string[]]$Arguments)
    & docker compose @composeArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Perintah docker compose gagal: $($Arguments -join ' ')"
    }
}
function Reset-ComposeDatabase {
    param([string]$Database, [string]$Owner)
    $safeDatabase = $Database.Replace('"', '""')
    $safeOwner = $Owner.Replace('"', '""')
    Invoke-Compose @("exec", "-T", "db", "psql", "--username", $Owner, "--dbname", "template1", "-v", "ON_ERROR_STOP=1",
        "-c", ('DROP DATABASE IF EXISTS "{0}" WITH (FORCE);' -f $safeDatabase))
    Invoke-Compose @("exec", "-T", "db", "psql", "--username", $Owner, "--dbname", "template1", "-v", "ON_ERROR_STOP=1",
        "-c", ('CREATE DATABASE "{0}" WITH OWNER = "{1}" TEMPLATE = template0;' -f $safeDatabase, $safeOwner))
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $backendDir "backups"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$sourceBackup = Join-Path $backupDir "news-db-source-$timestamp.dump"
$targetBackup = Join-Path $backupDir "news-db-docker-before-import-$timestamp.dump"

try {
    Write-Host "Membuat backup database lokal ke folder sementara..."
    $env:PGPASSWORD = $sourcePassword
    & $pgDumpPath --host $sourceUri.Host --port $sourcePort --username $sourceUser --dbname $sourceDatabase `
        --format=custom --no-owner --no-acl --file $sourceBackup
    if ($LASTEXITCODE -ne 0) {
        throw "Backup database lokal gagal. Periksa DATABASE_URL dan pastikan PostgreSQL lama berjalan."
    }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Menyiapkan PostgreSQL Docker dan migrasi skema..."
Invoke-Compose @("up", "-d", "backend")

$backendId = ((& docker compose @composeArgs ps -q backend) -join "`n").Trim()
if ($LASTEXITCODE -ne 0 -or -not $backendId) {
    throw "Container backend tidak ditemukan setelah Compose dijalankan."
}

$backendHealthy = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    $health = (& docker inspect --format '{{.State.Health.Status}}' $backendId 2>$null).Trim()
    if ($health -eq "healthy") { $backendHealthy = $true; break }
    if ($health -eq "unhealthy") { throw "Backend tidak sehat. Lihat docker compose logs backend sebelum melanjutkan." }
    Start-Sleep -Seconds 3
}
if (-not $backendHealthy) {
    throw "Backend belum sehat. Tidak ada restore yang dilakukan. Lihat docker compose logs backend."
}

$targetUser = $settings["POSTGRES_USER"]
$targetDatabase = $settings["POSTGRES_DB"]
$targetCountOutput = & docker compose @composeArgs exec -T db psql --username $targetUser --dbname $targetDatabase -At -F "," `
    -c "SELECT (SELECT COUNT(*) FROM users), (SELECT COUNT(*) FROM news);"
if ($LASTEXITCODE -ne 0) { throw "Tidak dapat memeriksa isi database Docker; tidak ada restore yang dilakukan." }
$targetCounts = ((($targetCountOutput | Select-Object -Last 1) -as [string]).Trim()).Split(',')
if ($targetCounts.Count -ne 2) { throw "Hasil pemeriksaan database Docker tidak dikenali; tidak ada restore yang dilakukan." }
$targetHasData = ([int]$targetCounts[0] -gt 0) -or ([int]$targetCounts[1] -gt 0)
if ($targetHasData -and -not $Force) {
    throw "Database Docker sudah berisi data. Tidak ada data yang diubah. Jalankan lagi dengan -Force hanya jika memang ingin menggantinya; skrip akan membuat backup target terlebih dahulu."
}

if ($targetHasData -or $Force) {
    Write-Host "Membackup database Docker yang akan diganti..."
    Invoke-Compose @("exec", "-T", "db", "pg_dump", "--username", $targetUser, "--dbname", $targetDatabase,
        "--format=custom", "--no-owner", "--no-acl", "--file", "/tmp/news-db-target-before-import.dump")
    Invoke-Compose @("cp", "db:/tmp/news-db-target-before-import.dump", $targetBackup)
}

$backendContainerId = ((& docker compose @composeArgs ps -q backend) -join "`n").Trim()
if ($backendContainerId) { Invoke-Compose @("stop", "backend") }
$frontendContainerId = ((& docker compose @frontendComposeArgs ps -q frontend) -join "`n").Trim()
if ($frontendContainerId) {
    & docker compose @frontendComposeArgs stop frontend
    if ($LASTEXITCODE -ne 0) { throw "Tidak dapat menghentikan frontend sebelum import." }
}

try {
    Write-Host "Memindahkan backup database lama ke container PostgreSQL..."
    Invoke-Compose @("cp", $sourceBackup, "db:/tmp/news-db-source.dump")
    Reset-ComposeDatabase -Database $targetDatabase -Owner $targetUser
    Invoke-Compose @("exec", "-T", "db", "pg_restore", "--username", $targetUser, "--dbname", $targetDatabase,
        "--no-owner", "--no-acl", "--exit-on-error", "/tmp/news-db-source.dump")
    Invoke-Compose @("exec", "-T", "db", "psql", "--username", $targetUser, "--dbname", $targetDatabase,
        "-c", "DROP TABLE IF EXISTS alembic_version")
} catch {
    throw "Restore berhenti. Backend dan frontend dibiarkan berhenti agar database parsial tidak menerima request. Backup lokal tersimpan di $sourceBackup. Detail: $($_.Exception.Message)"
}

Write-Host "Menjalankan kembali stack. Backend akan menerapkan Alembic pada skema hasil restore..."
Invoke-Compose @("up", "--build", "-d", "backend")

$backendId = ((& docker compose @composeArgs ps -q backend) -join "`n").Trim()
$backendHealthy = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    $health = (& docker inspect --format '{{.State.Health.Status}}' $backendId 2>$null).Trim()
    if ($health -eq "healthy") { $backendHealthy = $true; break }
    if ($health -eq "unhealthy") { throw "Backend gagal setelah restore. Backup lokal tersimpan di $sourceBackup." }
    Start-Sleep -Seconds 3
}
if (-not $backendHealthy) { throw "Backend belum sehat setelah restore. Backup lokal tersimpan di $sourceBackup." }

& docker compose @frontendComposeArgs up --build -d frontend
if ($LASTEXITCODE -ne 0) { throw "Database berhasil diimpor, tetapi frontend gagal dijalankan. Backup lokal tersimpan di $sourceBackup." }

$verifiedCounts = & docker compose @composeArgs exec -T db psql --username $targetUser --dbname $targetDatabase -At -F "," `
    -c "SELECT (SELECT COUNT(*) FROM users), (SELECT COUNT(*) FROM news);"
if ($LASTEXITCODE -ne 0) { throw "Restore selesai, tetapi pemeriksaan akhir gagal. Backup lokal tersimpan di $sourceBackup." }

Invoke-Compose @("exec", "-T", "db", "rm", "-f", "/tmp/news-db-source.dump")
Write-Host "Import selesai. Jumlah akun dan berita di Docker (users, news): $((($verifiedCounts | Select-Object -Last 1) -as [string]).Trim())"
Write-Host "Backup database lama disimpan di: $sourceBackup"
if ($targetHasData -or $Force) { Write-Host "Backup database Docker sebelumnya disimpan di: $targetBackup" }
