# Auth And Admin Boundary

## Identity Separation
- `UserProfile` remains a business-domain record for research users and paper ownership.
- `AdminAccount` is the only human login identity in v1.
- `AdminRefreshToken` stores revocable refresh sessions without coupling login state to business entities.
- `AuditLog` captures security-sensitive actions across auth, admin management, business writes, pulse runs, and ops actions.

## Token Model
- Human admins authenticate with `POST /auth/login`.
- Successful login returns:
  - a short-lived JWT access token
  - an opaque refresh token backed by `admin_refresh_tokens`
- `POST /auth/refresh` rotates the refresh token and revokes the previously used one.
- `POST /auth/logout` revokes the submitted refresh token for the authenticated admin session.
- Access tokens carry:
  - admin account id
  - email
  - role
  - issuer and audience claims

## Role Matrix
- `viewer`
  - allowed: business `GET` endpoints, pulse preview
  - blocked: business writes, pulse run, admin routes, mutation-style ops actions
- `operator`
  - allowed: all viewer routes, business writes, pulse run, scheduler tick, replay, requeue
  - blocked: admin-account management, audit-log reads
- `super_admin`
  - allowed: all operator routes
  - allowed: create/update admin accounts, set admin passwords, read audit logs
- `service`
  - allowed: `GET /health/ready`, `GET /ops/*`, `POST /ops/scheduler/tick`, `POST /ops/delivery-jobs/{delivery_job_id}/requeue`, `POST /ops/pulse-jobs/{pulse_job_id}/replay`
  - blocked: business CRUD and admin-management endpoints

## Internal Service Boundary
- Internal callers authenticate with `APP_INTERNAL_SERVICE_TOKEN`.
- This token is intentionally narrower than admin auth.
- It exists for monitoring, schedulers, and future internal integrations.
- It must not be reused as a customer or human admin credential.

## Audit Log Model
- Each audit row stores:
  - actor type, actor id, actor label
  - action
  - resource type and resource id
  - request id
  - route and method
  - status code
  - metadata JSON
  - created timestamp
- Recorded events in v1 include:
  - login success and failure
  - refresh and logout
  - admin account create, update, and password change
  - business writes on users, papers, progress events, signal snapshots, and subscription policies
  - pulse run
  - scheduler tick
  - replay and requeue
- Audit logging is best-effort. Primary requests should not fail just because audit persistence fails.

## Bootstrap Workflow
- Apply migrations:
  - `make migrate`
- Create or update the bootstrap super admin:
  - `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!'`
- Optional display name:
  - `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!' DISPLAY_NAME='Ops Admin'`
- Log in through `POST /auth/login` to obtain the access and refresh tokens for API use.

## Local Development Flow
- Start infra with `make docker-up`.
- Run `make migrate`.
- Bootstrap the initial admin.
- Optionally run `make seed`.
- Start API, worker, and scheduler as needed.
- Use `/docs` with the bearer token from `/auth/login` for protected route exploration.

## Known Limitations
- No customer-facing login is implemented in this phase.
- No OAuth, OIDC, or SSO integration is included.
- No password reset email workflow exists yet.
- JWT signing uses a shared secret from settings rather than key rotation infrastructure.
- Internal service auth is a single bearer token, suitable only for low-complexity internal deployments.

## Future Work
- Add customer auth as a separate identity boundary from `AdminAccount`.
- Add SSO/OIDC for admins after the current role boundary is stable.
- Add token rotation and secret management for production deployments.
- Extend audit review workflows with retention, export, and alerting.
