# Admin and writer accounts

Apply database changes with `alembic upgrade head` from `backend-news` (Docker Compose runs this before starting the API). The migrations add `users.phone` and `users.address`, create the short-lived `captcha_challenges` table, and convert every role except an explicitly assigned `admin` or `writer` to `writer`. New public registrations always get the `writer` role. There is no admin signup route. See [MIGRATIONS.md](MIGRATIONS.md) for local and Docker setup.

To provision the first admin, create the account through the existing users table or promote an existing trusted account directly in PostgreSQL:

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

Set a known password for that account before using the admin login. Admins sign in at `/dashboard`; they can add, view, and delete writer accounts. If an admin deletes a writer, the writer's published stories remain and are reassigned to that admin so their image URLs and Cloudinary assets remain attached to existing stories.

Writers can self-register with name, email, phone, address, CAPTCHA, and matching password fields at `BACKEND_PUBLIC_URL/writer/signup`, sign in with CAPTCHA at `BACKEND_PUBLIC_URL/writer/login`, and manage their own stories at `BACKEND_PUBLIC_URL/writer/dashboard`. Admin login at `BACKEND_PUBLIC_URL/dashboard` and API login at `BACKEND_PUBLIC_URL/api/auth/login` also require CAPTCHA. Authentication and account management pages live on the backend service; the frontend news site does not provide login or registration pages. Writers can update their name, email, phone, address, or password from `BACKEND_PUBLIC_URL/writer/profile`; saving profile changes requires their current password, and password changes require confirmation. Story ownership comes from the signed login session; the API ignores client-supplied author IDs and rejects attempts to update or delete another writer's story. Category writes are restricted to logged-in admins as well.

Set `SESSION_SECRET` to a long random value in `.env`. Set `COOKIE_SECURE=true` when serving the backend over HTTPS. Existing plaintext passwords are converted to PBKDF2 hashes on the first successful login.
