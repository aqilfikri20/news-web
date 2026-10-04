[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$BackupPath,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$backendDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot = Split-Path -Parent $backendDir
$frontendDir = Join-Path $repoRoot "frontend-news"
$envPath = Join-Path $backendDir ".env"
$composePath = Join-Path $backendDir "docker-compose.yml"
$frontendComposePath = Join-Path $frontendDir "docker-compose.yml"
if (-not (Test-Path -LiteralPath $envPath)) { throw "backend-news/.env tidak ditemukan." }
if (-not [System.IO.Path]::IsPathRooted($BackupPath)) { $BackupPath = Join-Path $repoRoot $BackupPath }
if (-not (Test-Path -LiteralPath $BackupPath -PathType Leaf)) { throw "File backup tidak ditemukan: $BackupPath" }
$BackupPath = (Resolve-Path -LiteralPath $BackupPath).Path
if (-not $Force) { throw "Restore akan mengganti isi database tujuan. Tinjau file backup lalu jalankan kembali dengan -Force." }

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
$frontendComposeArgs = @("compose", "--env-file", $envPath, "--project-directory", $frontendDir, "-f", $frontendComposePath)
$null = & docker info --format '{{.ServerVersion}}' 2>$null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine tidak dapat diakses. Pastikan Docker Desktop berjalan." }
$dbId = ((& docker @composeArgs ps -q db) -join "`n").Trim()
if ($LASTEXITCODE -ne 0 -or -not $dbId) { throw "Container database belum dibuat. Jalankan docker compose up -d db terlebih dahulu." }

$restoreId = [guid]::NewGuid().ToString('N')
$remoteSource = "/tmp/news-db-restore-$restoreId.dump"
$remoteTarget = "/tmp/news-db-before-restore-$restoreId.dump"
$targetBackup = Join-Path (Join-Path $backendDir "backups") ("news-before-restore-{0}.dump" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path (Split-Path -Parent $targetBackup) -Force | Out-Null
$backendId = ((& docker @composeArgs ps -q backend) -join "`n").Trim()
$frontendId = ((& docker @frontendComposeArgs ps -q frontend) -join "`n").Trim()
$backendWasRunning = $false
$frontendWasRunning = $false
if ($backendId) { $backendWasRunning = ((& docker inspect --format '{{.State.Running}}' $backendId 2>$null).Trim() -eq "true") }
if ($frontendId) { $frontendWasRunning = ((& docker inspect --format '{{.State.Running}}' $frontendId 2>$null).Trim() -eq "true") }

try {
    Write-Host "Membuat backup database Docker sebelum restore..."
    & docker @composeArgs exec -T db pg_dump --username $settings["POSTGRES_USER"] --dbname $settings["POSTGRES_DB"] `
        --format=custom --no-owner --no-acl --file $remoteTarget
    if ($LASTEXITCODE -ne 0) { throw "Backup database tujuan gagal; restore dibatalkan." }
    & docker @composeArgs cp "db:$remoteTarget" $targetBackup
    if ($LASTEXITCODE -ne 0) { throw "Gagal menyimpan backup database tujuan; restore dibatalkan." }

    if ($backendWasRunning) { & docker @composeArgs stop backend | Out-Null; if ($LASTEXITCODE -ne 0) { throw "Tidak dapat menghentikan backend." } }
    if ($frontendWasRunning) { & docker @frontendComposeArgs stop frontend | Out-Null; if ($LASTEXITCODE -ne 0) { throw "Tidak dapat menghentikan frontend." } }

    & docker @composeArgs cp $BackupPath "db:$remoteSource"
    if ($LASTEXITCODE -ne 0) { throw "Gagal menyalin file restore ke container." }
    & docker @composeArgs exec -T db pg_restore --list $remoteSource | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "File backup tidak dapat dibaca oleh pg_restore di PostgreSQL Docker. Database belum diubah." }

    Write-Host "Membuat database tujuan kosong agar foreign key lama tidak menghalangi restore..."
    $dbName = $settings["POSTGRES_DB"].Replace('"', '""')
    $dbUser = $settings["POSTGRES_USER"].Replace('"', '""')
    & docker @composeArgs exec -T db psql --username $settings["POSTGRES_USER"] --dbname template1 -v ON_ERROR_STOP=1 `
        -c ('DROP DATABASE IF EXISTS "{0}" WITH (FORCE);' -f $dbName)
    if ($LASTEXITCODE -ne 0) { throw "Tidak dapat mengosongkan database tujuan. Backup tujuan: $targetBackup" }
    & docker @composeArgs exec -T db psql --username $settings["POSTGRES_USER"] --dbname template1 -v ON_ERROR_STOP=1 `
        -c ('CREATE DATABASE "{0}" WITH OWNER = "{1}" TEMPLATE = template0;' -f $dbName, $dbUser)
    if ($LASTEXITCODE -ne 0) { throw "Tidak dapat membuat ulang database tujuan. Backup tujuan: $targetBackup" }

    Write-Host "Memulihkan database dari backup..."
    & docker @composeArgs exec -T db pg_restore --username $settings["POSTGRES_USER"] --dbname $settings["POSTGRES_DB"] `
        --no-owner --no-acl --exit-on-error $remoteSource
    if ($LASTEXITCODE -ne 0) { throw "Restore gagal. Backend dan frontend dibiarkan berhenti; backup tujuan tersedia di $targetBackup" }
    & docker @composeArgs exec -T db psql --username $settings["POSTGRES_USER"] --dbname $settings["POSTGRES_DB"] `
        -c "DROP TABLE IF EXISTS alembic_version"
    if ($LASTEXITCODE -ne 0) { throw "Data dipulihkan, tetapi penyiapan migrasi gagal. Backup tujuan: $targetBackup" }

    & docker @composeArgs up --build -d backend
    if ($LASTEXITCODE -ne 0) { throw "Data dipulihkan, tetapi aplikasi belum berhasil dijalankan. Backup tujuan: $targetBackup" }
    & docker @frontendComposeArgs up --build -d frontend
    if ($LASTEXITCODE -ne 0) { throw "Data dipulihkan, backend berjalan, tetapi frontend belum berhasil dijalankan. Backup tujuan: $targetBackup" }
} catch {
    throw "Restore belum selesai. Backup database tujuan tersimpan di $targetBackup. Detail: $($_.Exception.Message)"
} finally {
    & docker @composeArgs exec -T db rm -f $remoteSource $remoteTarget 2>$null | Out-Null
}

Write-Host "Restore selesai. Backup database sebelum restore tersimpan di: $targetBackup"
