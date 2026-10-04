# Panduan Docker, Backup, dan Restore Database

Proyek memakai dua Docker Compose project terpisah. File compose dan operasi database berada di folder backend; compose frontend berada di folder frontend:

- Backend/API dan PostgreSQL: `backend-news/docker-compose.yml`
- Frontend/Nginx: `frontend-news/docker-compose.yml`
- Skrip database: `backend-news/scripts/`
- Arsip backup lokal: `backend-news/backups/` (diabaikan Git)

## Pengaturan sebelum menjalankan

Pastikan `backend-news/.env` ada dan berisi nilai sendiri, bukan nilai contoh dari `.env.example`. Cocokkan `POSTGRES_USER`, `POSTGRES_PASSWORD`, dan `POSTGRES_DB` dengan kredensial pada `DATABASE_URL`. `DATABASE_URL` di `.env` menunjuk ke database sumber lokal; Compose mengubah host database backend menjadi service `db` secara internal.

Frontend memanggil API langsung, jadi pastikan:

- `BACKEND_PUBLIC_URL` menunjuk ke URL backend yang dapat dicapai browser. Lokal: `http://localhost:8000`.
- `CORS_ORIGINS` memuat origin frontend yang dipakai. Lokal: `http://localhost:8080` dan, jika menjalankan Vite, `http://localhost:5173`.
- Jika port atau domain berbeda, perbarui kedua nilai tersebut. Build ulang frontend setelah mengganti `BACKEND_PUBLIC_URL`.

> Jangan kirim isi `.env` ke orang lain atau commit ke Git. Password URL perlu di-URL-encode jika berisi karakter khusus.

## Jalankan masing-masing Docker

Pastikan Docker Desktop aktif. Jalankan backend terlebih dahulu dari PowerShell:

```powershell
cd D:\news-website\backend-news
docker compose --env-file .env config -q
docker compose --env-file .env up --build -d
docker compose --env-file .env ps
```

Tunggu `db` berstatus `healthy` dan `backend` berstatus `healthy`. Alembic berjalan otomatis sebelum API mulai.

Buka PowerShell kedua untuk menjalankan frontend sendiri:

```powershell
cd D:\news-website\frontend-news
docker compose --env-file ..\backend-news\.env config -q
docker compose --env-file ..\backend-news\.env up --build -d
docker compose --env-file ..\backend-news\.env ps
```

Frontend tersedia di `http://localhost:8080`; backend dan dashboard pengelola di `http://localhost:8000`.

Untuk mematikan service, jalankan `docker compose --env-file .env down` dari `backend-news` dan `docker compose --env-file ..\backend-news\.env down` dari `frontend-news`. Perintah `down` tanpa `-v` mempertahankan volume database. **Jangan gunakan `down -v` atau menghapus volume PostgreSQL jika data perlu dipertahankan.** Menghapus container dan image saja tidak menghapus named volume.

## Pindahkan database lokal lama ke Docker

Pastikan `DATABASE_URL` di `backend-news/.env` menunjuk ke database PostgreSQL lokal yang berisi berita dan akun. Jalankan dari root proyek:

```powershell
cd D:\news-website
.\backend-news\scripts\import-local-db-to-docker.ps1
```

Skrip membuat backup dari database sumber, memeriksa target, memulihkan data, lalu menjalankan backend dan frontend terpisah. Arsip sumber dan backup target disimpan di `backend-news/backups`. Skrip mencari `pg_dump` di `PATH` atau di instalasi PostgreSQL; pada komputer ini PostgreSQL 18 berada di `C:\Program Files\PostgreSQL\18\bin`.

Jika target sudah memiliki akun atau berita, skrip berhenti tanpa menimpanya. `-Force` mengganti seluruh database target, tetapi membuat backup target lebih dulu:

```powershell
.\backend-news\scripts\import-local-db-to-docker.ps1 -Force
```

## Backup database Docker ke komputer

Jalankan dari root proyek saat backend database hidup:

```powershell
cd D:\news-website
.\backend-news\scripts\backup-docker-db.ps1
```

File backup custom-format akan dibuat di `backend-news/backups` dengan timestamp. Untuk menentukan nama file:

```powershell
.\backend-news\scripts\backup-docker-db.ps1 `
  -OutputPath ".\backend-news\backups\sebelum-perubahan.dump"
```

Simpan salinan backup di media/lokasi lain juga. Backup yang hanya tersimpan di komputer yang sama tidak melindungi dari kerusakan atau kehilangan komputer.

## Restore backup ke Docker

Perintah restore akan membuat backup database tujuan saat ini, menghentikan frontend dan backend, membuat ulang database tujuan dari file backup, lalu menjalankan kedua Compose project kembali. Restore mengganti isi database tujuan dan karena itu memerlukan `-Force`:

```powershell
.\backend-news\scripts\restore-docker-db.ps1 `
  -BackupPath ".\backend-news\backups\NAMA-BACKUP.dump" `
  -Force
```

Ganti nama file dengan file yang ada. Backup sebelum restore dibuat otomatis di `backend-news/backups`. Jangan hapus backup sumber atau target sampai berita dan akun sudah diverifikasi di website.

## Verifikasi dan pemulihan jika gagal

```powershell
cd D:\news-website\backend-news
docker compose --env-file .env ps
docker compose --env-file .env logs --tail 100 backend
docker compose --env-file .env exec backend alembic current
```

Revisi Alembic seharusnya menunjukkan `head`. Untuk menghitung berita tanpa menebak username/database, gunakan nilai dari `.env`:

```powershell
$config = @{}
Get-Content .env | ForEach-Object {
  if ($_ -match '^(POSTGRES_USER|POSTGRES_DB)=(.*)$') {
    $config[$Matches[1]] = $Matches[2].Trim()
  }
}
docker compose --env-file .env exec -T db psql `
  -U $config["POSTGRES_USER"] -d $config["POSTGRES_DB"] `
  -c "SELECT COUNT(*) AS jumlah_berita FROM news;"
```

Jika restore gagal, skrip membiarkan aplikasi berhenti dan mempertahankan backup target. Jangan hapus volume atau backup. Periksa pesan error; setelah penyebab diperbaiki, restore ulang dari backup yang benar. Pastikan file sumber memang memuat berita sebelum menggunakannya.
