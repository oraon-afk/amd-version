# Authentication Structure

## Requirements

- User registration
- Email/password login
- Password hashing
- JWT access tokens
- Refresh token support
- Protected dashboard access

## Backend Modules

```text
app/auth/password_service.py
  Hash and verify passwords.

app/auth/jwt_service.py
  Create and validate JWT access and refresh tokens.

app/auth/auth_dependencies.py
  FastAPI dependencies for current user and protected routes.

app/api/v1/auth.py
  Register, login, refresh, logout.

app/api/v1/users.py
  Current user profile endpoint.
```

## Database Tables

```text
users
  id
  organization_id
  email
  password_hash
  full_name
  role
  is_active
  created_at
  updated_at

refresh_tokens
  id
  user_id
  token_hash
  expires_at
  revoked_at
  created_at
```

## Frontend Modules

```text
features/auth/api.ts
features/auth/hooks.ts
features/auth/types.ts
features/auth/components/LoginForm.tsx
features/auth/components/RegisterForm.tsx
```

## Security Guidance

- Never store raw passwords.
- Do not put secrets in frontend environment variables.
- Prefer HttpOnly secure cookies for production token storage.
- Keep access tokens short-lived.
- Store only refresh token hashes in the database.

