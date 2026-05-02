# TwinVal Field Observation Portal

A certified field-data capture system for civil engineering interns deployed at
IIUM campus buildings. Every submission is a timestamped, cryptographically
chained human observation record that feeds TwinVal's Confidence Index (CI)
layer (Indian Patent Application No. 202641030498).

This is a sibling app to TwinVal's REIT and Personal dashboards. It is not a
notes app — it is an audit-grade capture portal.

```
┌──────────────────────────────────────────────────────────────────┐
│  twinval.com/entry  ──►  Vercel rewrite  ──►  Portal Vercel app  │
│       (React + TS)          (path mount)        base="/entry/"   │
│           │                                                      │
│           └── HTTPS + httpOnly cookies ──►  FastAPI on Railway   │
│                                                  │               │
│                                                  ├── Postgres    │
│                                                  └── Cloudflare  │
│                                                       R2 (S3)    │
└──────────────────────────────────────────────────────────────────┘
```

## What's in the box

```
twinval-portal/
├── backend/                  FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── models/           ORM models (users, owners, properties, ...)
│   │   ├── routers/          FastAPI endpoints
│   │   ├── schemas/          Pydantic request/response schemas
│   │   ├── services/         hash_chain, auth, access_control, storage
│   │   ├── deps.py           Auth + DB DI
│   │   ├── config.py         Settings (env-driven)
│   │   ├── database.py       Engine + session factory
│   │   └── main.py           App factory + lifespan + router wiring
│   ├── alembic/              Migrations
│   ├── tests/                90 tests covering chain logic + every API surface
│   ├── Dockerfile
│   ├── railway.json
│   └── requirements.txt
├── frontend/                 React + Vite + Tailwind
│   ├── src/
│   │   ├── components/       Layout, ProtectedRoute, SeverityBadge, ...
│   │   ├── contexts/         AuthContext
│   │   ├── lib/              api.ts, format.ts
│   │   ├── pages/            Login, Dashboard, Submit, History, Detail, Admin
│   │   └── types/api.ts      TypeScript mirror of backend Pydantic schemas
│   ├── vercel.json           Path-mount rewrites for /entry
│   └── package.json
├── docker-compose.yml        Local dev: postgres + backend with hot reload
└── README.md
```

## Local development

### Quickstart with Docker

```bash
# From twinval-portal/
docker compose up -d              # postgres + backend on :8000
cd frontend && npm install && npm run dev   # vite dev server on :5173/entry/
```

The first boot creates the bootstrap admin from `INITIAL_ADMIN_*` env vars
(set in `docker-compose.yml`). Sign in with:

- email: `admin@twinval.local`
- password: `change-me-on-first-login`

Visit `http://localhost:5173/entry/` and you should land on the login page.

### Manual setup (without Docker)

**Backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate           # Windows; use source on macOS/Linux
pip install -r requirements.txt
cp .env.example .env             # then edit DATABASE_URL etc
alembic upgrade head             # apply migrations
uvicorn app.main:app --reload    # http://localhost:8000
```

**Frontend**

```bash
cd frontend
cp .env.example .env             # leave VITE_API_BASE_URL empty in dev (vite proxy)
npm install
npm run dev                      # http://localhost:5173/entry/
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`, so the
frontend talks to FastAPI without CORS configuration during dev.

### Running the tests

```bash
cd backend
.venv/Scripts/python -m pytest tests/    # 90 tests, ~30 s
```

```bash
cd frontend
npm run typecheck    # tsc --noEmit
npm run build        # full production build
```

## Environment variables

### Backend ([backend/.env.example](backend/.env.example))

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://...` — required in prod |
| `JWT_SECRET` | Long random string. **Rotate on compromise.** |
| `ACCESS_TOKEN_TTL_MINUTES` | Default 30 |
| `REFRESH_TOKEN_TTL_DAYS` | Default 14 |
| `INITIAL_ADMIN_EMAIL` / `_PASSWORD` / `_NAME` | Bootstrap admin on first boot. Idempotent — skipped if any admin exists. |
| `CORS_ORIGINS` | Comma-separated origins for the SPA |
| `S3_ENDPOINT_URL` | Cloudflare R2 endpoint. Leave blank for stub mode. |
| `S3_BUCKET` / `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` / `S3_REGION` | R2 credentials |
| `S3_PUBLIC_BASE_URL` | Public CDN base URL for photos (e.g. `https://photos.twinval.com`) |
| `GENESIS_SEED` | **Do not change after launch.** Anchors the chain. |
| `LOGIN_RATE_LIMIT` | Default `10/15minutes` per IP |
| `MAX_PHOTO_BYTES` | Default 5 MB |
| `ALLOWED_PHOTO_MIME_TYPES` | Default JPEG, PNG, WEBP, HEIC |

### Frontend ([frontend/.env.example](frontend/.env.example))

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | Empty in dev (vite proxy handles `/api/*`). In prod, set to backend origin (e.g. `https://entry-api.twinval.com`). |

## Database migrations

```bash
cd backend
# Apply all pending migrations
alembic upgrade head

# Generate a new revision after editing models
alembic revision --autogenerate -m "describe what changed"

# Roll back one step (rare — usually we forward-fix)
alembic downgrade -1

# Check current revision
alembic current
```

Production migrations run automatically on every container boot — see the
`CMD` in [backend/Dockerfile](backend/Dockerfile) and the `startCommand` in
[backend/railway.json](backend/railway.json). This is safe because Alembic is
idempotent: applied migrations are tracked in the `alembic_version` table.

## Hash chain audit

Every observation entry is anchored to a SHA-256 hash of its canonical
payload, including the previous entry's hash. Tampering with any field —
including the human-readable snapshot fields — invalidates the entry's hash
and breaks the chain link to its successor.

### Audit anchors

- **Genesis seed**: `TWINVAL_GENESIS_IIUM_PILOT`
- **Genesis hash**: `5f0255e4b9627ccf79f293d3f55daacc6ef7a493faa7ecdba98eb7507d245e08`

This pair is pinned in [test_hash_chain.py](backend/tests/test_hash_chain.py)
and recomputed on every test run. If the test starts failing, the genesis
seed has been altered and **the entire chain must be re-verified**.

### Canonical payload (16 fields, sorted, no whitespace)

```
building_label, description, entry_ref_id, intern_id, observation_type,
owner_profile_id, owner_profile_name, photo_url, prev_hash, property_id,
property_name, sensor_zone_id, severity, stream, submitted_at, zone_label
```

Both the foreign keys (`property_id`, `sensor_zone_id`, `owner_profile_id`)
and the human-readable snapshots (`property_name`, `building_label`,
`zone_label`, `owner_profile_name`, `stream`) are part of the hash. The
snapshots make every entry self-contained: even if upstream rows are later
renamed or archived, the entry verifies forever.

### Verifying the chain

**Per entry** (any authenticated user with access):

```
GET /observations/{id}/verify
→ { valid: bool, computed_hash, stored_hash, chain_intact: bool }
```

**Full chain** (admin only):

```
GET /admin/chain/verify
→ { total_entries, broken_links: [entry_ref_ids], chain_valid: bool }
```

Or via the admin UI at `/admin` → **Chain Audit** tab.

### What to do if a break is detected

1. **Do not panic.** A break does not mean the chain is wrong — it means
   the database state diverges from what the chain originally recorded.
2. Identify the broken `entry_ref_id` from the audit response.
3. Compare the current row against the most recent backup or audit log.
4. If the row was tampered with, restore from backup. The chain
   immediately becomes valid again because the original hash matches the
   restored payload.
5. If the divergence was a legitimate edit (which should never happen —
   the API does not expose any UPDATE on chain-relevant fields), the chain
   must be re-genesis'd or branched. Escalate before doing this — it
   destroys the audit trail.

## Deployment

### Backend → Railway

1. Create a Railway project. Add a Postgres add-on.
2. Point the service at this repo's `twinval-portal/backend` directory
   (Railway auto-detects [railway.json](backend/railway.json) and
   [Dockerfile](backend/Dockerfile)).
3. Set environment variables (see backend table above). At minimum:
   `DATABASE_URL` (auto-injected by the Postgres add-on),
   `JWT_SECRET`, `INITIAL_ADMIN_*`, `CORS_ORIGINS`, `S3_*`.
4. Deploy. The container runs `alembic upgrade head` then starts uvicorn
   bound to `$PORT`. The `/health` endpoint is wired up for Railway's
   healthcheck.
5. Note the public URL (e.g. `https://entry-api.twinval.com`) — you'll
   need it for the frontend's `VITE_API_BASE_URL`.

### Frontend → Vercel (mounted at `twinval.com/entry`)

The portal is its own Vercel project. The main `twinval.com` Vercel project
proxies `/entry/*` to it.

**Step 1.** Deploy the portal as a standalone Vercel project:

- Root directory: `twinval-portal/frontend`
- Framework preset: Vite (auto-detected via [vercel.json](frontend/vercel.json))
- Build command: `npm run build`
- Output directory: `dist`
- Env var: `VITE_API_BASE_URL=https://entry-api.twinval.com` (your Railway origin)

The portal's [vercel.json](frontend/vercel.json) handles its own
SPA fallback and asset serving under `/entry/*` — no changes needed.

**Step 2.** Add a rewrite to the existing `twinval.com` Vercel project so
`/entry/*` proxies to the portal. In that project's `vercel.json`, add:

```json
{
  "rewrites": [
    { "source": "/entry", "destination": "https://twinval-portal.vercel.app/entry" },
    { "source": "/entry/:path*", "destination": "https://twinval-portal.vercel.app/entry/:path*" }
  ]
}
```

(Replace `twinval-portal.vercel.app` with the portal project's actual
deployment domain.)

**Step 3.** Verify:

- `https://twinval.com/entry` redirects to login
- Sign in as the bootstrap admin
- Submit a test observation — confirm `entry_hash` and `entry_ref_id` are
  returned, and the `Verify Integrity` button reports `valid: true,
  chain_intact: true`

## Architecture notes

### Roles & access control

| Role | Read | Write | Notes |
|---|---|---|---|
| `intern` | Own observations only | Submit observations, enrol owners / properties / zones | The data-capture role |
| `admin` | Everything | Everything + register users + issue grants + chain audit + review | TwinVal staff |
| `stakeholder` | Scoped via `access_grants` | None | REIT manager, lender risk officer, individual owner |
| `auditor` | Everything (read-only) | None | Compliance / regulator |

Stakeholder grants come in four scope kinds:

- `all` — unrestricted (rare; usually for auditors)
- `stream` — every property whose primary owner is in this stream
- `owner_profile` — every property owned by this counterparty
- `property` — one specific property

Per-grant permission flags (`can_view_observations`, `can_view_chain_audit`,
`can_view_financials`, `can_view_personal_data`) layer on top of scope.

### Atomic chain insertion

`insert_observation_atomic()` in
[hash_chain.py](backend/app/services/hash_chain.py) takes a `FOR UPDATE` lock
on the latest entry row before computing `prev_hash` and inserting. This
serialises concurrent submissions so the chain cannot fork.

(SQLite, used in the test suite, doesn't support row locking — concurrency
safety is a Postgres-only guarantee. Tests verify correctness; production
verifies correctness *and* concurrency.)

### Snapshot semantics

Every chain entry stores both the FKs (`property_id` etc.) and the
human-readable snapshot at submission time (`property_name` etc.). The
snapshot is part of the hash. So:

- Renaming a property after the fact does **not** break existing entries.
- Archiving an owner does **not** break existing entries.
- Tampering with a snapshot column on a chain row **does** break the entry's hash.

This is what makes the chain self-contained ten years from now.

## License

Proprietary. Copyright TwinVal. Patent pending — Indian Patent Application
No. 202641030498.
