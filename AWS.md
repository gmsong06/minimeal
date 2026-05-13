# AWS Integration

Minimeal uses **DynamoDB** as its production datastore for users and meal logs. The backend auto-detects whether AWS credentials are available and falls back to local JSON files when they are not, so no AWS account is needed for local development.

---

## Architecture

### Tables

| Table | Partition key | Sort key | Purpose |
|---|---|---|---|
| `minimeal-users` | `username` (S) | — | Account credentials + display names |
| `minimeal-meals` | `username` (S) | `meal_id` (S) | Per-user meal log entries |

Both tables use **PAY_PER_REQUEST** billing (no provisioned capacity to manage) and are tagged:

```
project=minimeal
managed-by=minimeal-backend
```

### Storage modes

Controlled by the `MINIMEAL_STORAGE_MODE` env var:

| Value | Behavior |
|---|---|
| `auto` (default) | Try DynamoDB first; fall back to local JSON if AWS is unreachable |
| `dynamodb` | Require DynamoDB; raise on failure |
| `local` | Always use local JSON files |

---

## How it works

All storage is routed through `StorageService` ([backend/app/services/storage.py](backend/app/services/storage.py)). On first use, `initialize()` is called automatically. It:

1. Tries to connect to DynamoDB and describe both tables.
2. Creates tables that don't exist yet (idempotent — safe to run repeatedly).
3. Waits for tables to become `ACTIVE`.
4. Seeds the three demo accounts if they don't already exist.

After that, every read/write operation (get meals, save meal, delete meal, set excluded status) is dispatched to either the DynamoDB or local path based on `active_backend`.

### Float handling

DynamoDB doesn't accept Python `float`s natively. The `_to_dynamodb_value` / `_from_dynamodb_value` helpers convert `float → Decimal` on write and `Decimal → int | float` on read, preserving numeric precision without leaking `Decimal` types to callers.

### Pagination

`_get_meals_dynamodb` loops on `LastEvaluatedKey` to handle users with more meals than DynamoDB returns in a single page (default 1 MB limit).

---

## Authentication

Minimeal uses simple shared-secret accounts (no JWTs). The `X-Minimeal-Username` HTTP header identifies the caller on every authenticated request. The auth flow:

1. `GET /auth/accounts` — returns the list of seeded demo accounts (username, password, display name).
2. `POST /auth/login` — validates credentials; returns `{ username, display_name }`.
3. All meal endpoints require `X-Minimeal-Username: <username>` and verify the username exists in the users table before proceeding.

---

## Setup

### Prerequisites

- AWS CLI configured with credentials that have DynamoDB read/write access in your target region.
- Backend virtualenv installed (`pip install -r requirements.txt` pulls `boto3`).

### First-time setup

Run once from `backend/` to create tables and seed demo accounts:

```bash
cd minimeal/backend
source .venv/bin/activate
MINIMEAL_STORAGE_MODE=dynamodb python scripts/setup_minimeal_aws.py
```

Expected output:

```
minimeal AWS setup complete
backend: dynamodb
users_table: minimeal-users
meals_table: minimeal-meals
seeded_accounts:
  - Alex (Demo): minimeal_alex / minimeal123
  - Riley (Demo): minimeal_riley / minimeal123
  - Jordan (Demo): minimeal_jordan / minimeal123
```

The script is safe to re-run — it won't overwrite existing users or recreate existing tables.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `MINIMEAL_STORAGE_MODE` | `auto` | `auto`, `dynamodb`, or `local` |
| `AWS_REGION` | `us-east-1` | DynamoDB region |
| `MINIMEAL_USERS_TABLE` | `minimeal-users` | Users table name |
| `MINIMEAL_MEALS_TABLE` | `minimeal-meals` | Meals table name |

AWS credentials are picked up from the standard boto3 credential chain (env vars, `~/.aws/credentials`, IAM role, etc.) — no special configuration needed beyond having credentials available.

---

## Demo accounts

Three accounts are seeded automatically for local testing and demos:

| Username | Password | Display name |
|---|---|---|
| `minimeal_alex` | `minimeal123` | Alex (Demo) |
| `minimeal_riley` | `minimeal123` | Riley (Demo) |
| `minimeal_jordan` | `minimeal123` | Jordan (Demo) |

---

## Local fallback

When `MINIMEAL_STORAGE_MODE=auto` and DynamoDB is unreachable (no credentials, no network), the backend writes to:

- `backend/users.json` — user accounts
- `backend/meal_log.json` — meal entries

Both files are gitignored. The same demo accounts are seeded into `users.json` on first run.
