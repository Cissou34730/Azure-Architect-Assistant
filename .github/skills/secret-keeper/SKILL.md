---
name: migrate-dotenv-to-secretkeeper
description: 'Migrate a codebase from .env / dotenv to SecretKeeper encrypted vault. USE FOR: replace dotenv, migrate .env, remove secret from .env, switch to SecretKeeper, convert environment variables to vault, replace process.env, replace os.environ, migrate secrets, encrypt .env, secure environment variables, dotenv to sk. DO NOT USE FOR: initial SecretKeeper setup without existing .env, general secret management questions, vault troubleshooting.'
argument-hint: 'Specify the language (python/typescript) and optionally the path to the .env file'
---

# Migrate .env / dotenv to SecretKeeper

Automated migration of codebases using `.env` files and dotenv libraries to SecretKeeper's encrypted vault.

## When to Use

- Project has `.env`, `.env.local`, or `.env.example` files with secrets
- Code uses `python-dotenv` / `load_dotenv()` / `os.environ` to read secrets
- Code uses `dotenv` / `process.env` in Node.js/TypeScript to read secrets
- User wants to encrypt existing plaintext secrets

## Prerequisites

Before starting, verify:
1. `sk.exe` is on PATH — run `sk --version` or `sk status` in terminal
2. If no vault exists yet, run `sk init` in the project root (interactive — needs user input)

## Procedure

### Phase 1: Discovery

1. **Find all .env files** in the project:
   - `.env`, `.env.local`, `.env.development`, `.env.production`, `.env.example`, `.env.test`
   - Check `.gitignore` for patterns like `*.env` or `.env*`

2. **Find all dotenv usage** in the codebase. Search for:
   - Python: `load_dotenv`, `dotenv_values`, `from dotenv`, `import dotenv`, `os.environ[`, `os.environ.get(`, `os.getenv(`
   - TypeScript/JavaScript: `dotenv`, `process.env.`, `import 'dotenv/config'`, `require('dotenv')`, `config()` from dotenv

3. **Catalog every environment variable** referenced in the code. Build a list of all keys.

4. **Classify each variable as SECRET or CONFIG:**

   **SECRETS** (→ migrate to SecretKeeper vault):
   - Passwords, tokens, API keys, private keys, signing secrets
   - Connection strings containing credentials
   - Any value whose exposure would be a security incident
   - Common patterns: `*_PASSWORD`, `*_SECRET`, `*_KEY`, `*_TOKEN`, `*_CREDENTIAL`, `*_PRIVATE_*`, `JWT_*`, `STRIPE_SECRET_*`, `AWS_SECRET_*`

   **CONFIG** (→ keep in plaintext env vars or config file):
   - Hostnames, ports, URLs without credentials
   - Log levels, environment names (`NODE_ENV`, `FLASK_ENV`)
   - Feature flags, timeouts, retry counts
   - File paths, locale settings
   - Common patterns: `*_HOST`, `*_PORT`, `*_URL` (without password), `*_LEVEL`, `*_ENV`, `*_TIMEOUT`, `*_ENABLED`

   **IMPORTANT:** Only migrate secrets. Config values must NOT go into the vault — they need to stay visible, diffable, and accessible without decryption.

5. **Check if vault exists**: look for `.secretkeeper/` directory. If not present, tell the user to run `sk init` first (this is interactive and cannot be automated).

### Phase 2: Import secrets

1. **Check if vault is unlocked**: run `sk status` in terminal
   - If locked, tell the user to run `sk unlock` (interactive)

2. **Import only secrets** into the vault. Two approaches:

   **Approach A (recommended):** Create a temporary file containing only the secret entries from `.env`, then import it:
   ```
   sk import-env secrets-only.env
   ```
   Then delete the temporary file.

   **Approach B:** Import the full `.env`, then remove config entries from the vault:
   ```
   sk import-env .env
   sk remove PORT
   sk remove LOG_LEVEL
   ```

3. **Verify import**: run `sk list` to confirm all expected **secret** keys are present (and no config keys slipped in)

### Phase 3: Code transformation

Apply these replacements **only to variables classified as SECRETS** in Phase 1. Leave CONFIG variables reading from `os.environ` / `process.env` as-is.

#### Python projects

**Remove dotenv setup code** (if ALL variables are migrated) **or keep it** (if some config vars still come from `.env`):
```python
# DELETE these lines only if no config vars remain in .env:
from dotenv import load_dotenv
load_dotenv()
```

**Add SecretKeeper import (once per file that reads secrets):**
```python
from secretkeeper import SecretKeeper

sk = SecretKeeper()
```

**Replace SECRET variable reads using this mapping (leave CONFIG reads unchanged):**

| Original pattern (for SECRETS only) | Replacement |
|---|---|
| `os.environ["SECRET_KEY"]` | `sk.get("SECRET_KEY")` |
| `os.environ.get("SECRET_KEY")` | `sk.get_or_none("SECRET_KEY")` |
| `os.environ.get("SECRET_KEY", "default")` | `sk.get_or_none("SECRET_KEY") or "default"` |
| `os.getenv("SECRET_KEY")` | `sk.get_or_none("SECRET_KEY")` |
| `os.getenv("SECRET_KEY", "default")` | `sk.get_or_none("SECRET_KEY") or "default"` |
| `"SECRET_KEY" in os.environ` | `sk.has("SECRET_KEY")` |

**Keep `os` import** if any config variables still use `os.environ` or `os.getenv`.

**Update dependencies:**
- Remove `python-dotenv` from `requirements.txt`, `pyproject.toml`, or `setup.cfg`
- Add `secretkeeper` dependency (local path install: `secretkeeper @ file:///path/to/SecretKeeper/sdk/python`)

#### TypeScript / JavaScript projects

**Remove dotenv setup code:**
```typescript
// DELETE these lines:
import 'dotenv/config';
// or
import dotenv from 'dotenv';
dotenv.config();
// or
require('dotenv').config();
```

**Add SecretKeeper import (once per file, at top).**

For async contexts (recommended):
```typescript
import { SecretKeeper } from 'secretkeeper';

const sk = new SecretKeeper();
```

For synchronous contexts:
```typescript
import { SecretKeeperSync } from 'secretkeeper';

const sk = new SecretKeeperSync();
```

**Replace SECRET variable reads using this mapping (leave CONFIG reads as `process.env.*`):**

| Original pattern (for SECRETS only) | Replacement (async) | Replacement (sync) |
|---|---|---|
| `process.env.SECRET_KEY!` | `await sk.get('SECRET_KEY')` | `sk.get('SECRET_KEY')` |
| `process.env.SECRET_KEY` | `await sk.getOrNull('SECRET_KEY')` | `sk.getOrNull('SECRET_KEY')` |
| `process.env.SECRET_KEY ?? 'default'` | `(await sk.getOrNull('SECRET_KEY')) ?? 'default'` | `sk.getOrNull('SECRET_KEY') ?? 'default'` |
| `process.env.SECRET_KEY \|\| 'default'` | `(await sk.getOrNull('SECRET_KEY')) ?? 'default'` | `sk.getOrNull('SECRET_KEY') ?? 'default'` |
| `'SECRET_KEY' in process.env` | `await sk.has('SECRET_KEY')` | `sk.has('SECRET_KEY')` |

**IMPORTANT for async:** If the containing function is not already `async`, you must make it `async` and update all callers to `await` the result. If this creates too much churn, use `SecretKeeperSync` instead.

**Update dependencies:**
- Remove `dotenv` from `package.json` dependencies
- Add `"secretkeeper": "file:../path/to/SecretKeeper/sdk/typescript"` to dependencies
- Run `npm install`

### Phase 4: Cleanup

1. **Split or delete .env files**:
   - If `.env` contained ONLY secrets: delete it
   - If `.env` had a mix: rewrite it to keep only config entries, remove all secret lines
   - Delete `.env.local` and any other files that contained secrets
2. **Keep .env.example** if it exists — update it to show only config entries and placeholder comments for secrets
3. **Update .gitignore**: keep `.env` entries if you still use `.env` for config; `.secretkeeper/vault.enc` is already gitignored by `sk init`
4. **Update README/docs**: replace any "copy .env.example to .env" instructions with SecretKeeper workflow:
   - `sk unlock` to cache password
   - `sk list` to see available secrets
5. **Uninstall dotenv packages**:
   - Python: remove `python-dotenv` from dependency files
   - TypeScript: `npm uninstall dotenv`

## Error Handling

When adding SecretKeeper calls, use appropriate error handling:

**Python:**
```python
from secretkeeper.exceptions import KeyNotFoundError, VaultLockedError

try:
    value = sk.get("KEY")
except KeyNotFoundError:
    value = "fallback"
except VaultLockedError:
    raise RuntimeError("Run 'sk unlock' in a terminal first")
```

**TypeScript:**
```typescript
import { KeyNotFoundError, VaultLockedError } from 'secretkeeper';

try {
  const value = sk.get('KEY');  // sync
} catch (e) {
  if (e instanceof KeyNotFoundError) { /* fallback */ }
  if (e instanceof VaultLockedError) { /* tell user to unlock */ }
}
```

## Validation

After migration:
1. Run the project's test suite to verify nothing is broken
2. Confirm no remaining references to `process.env.` or `os.environ` **for secrets** (config reads via `process.env`/`os.environ` are fine)
3. Confirm dotenv packages are removed from dependency files (unless still needed for config-only `.env`)
4. Confirm `.env` files no longer contain any secrets (they may still exist with config-only entries)

## Key Rules

- **Only migrate secrets, never config** — ports, hostnames, log levels, feature flags stay in plaintext
- **Never delete .env before confirming `sk list` shows all expected secret keys**
- **Never automate `sk init` or `sk unlock`** — these require interactive password input
- **One `SecretKeeper()` instance per module** — initialize at module level, not per-function
- **`sk.get()` throws on missing keys** — use `sk.get_or_none()` / `sk.getOrNull()` for optional values
- Valid key names: `^[A-Za-z_][A-Za-z0-9_.\.\-]*$`, max 256 characters
- **When in doubt, ask the user** whether a variable is a secret or config — don't guess
