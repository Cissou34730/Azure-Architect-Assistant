# UV Migration Guide for Other Worktrees

## Prerequisites
- Install `uv` if not already installed: `pip install uv`

## Steps to Migrate Each Worktree

### 1. Copy Configuration Files
From this worktree (`archchatbot`), copy these files to each other worktree:

```powershell
# From the archchatbot worktree root
$files = @("pyproject.toml", "uv.lock", ".python-version")
$targetWorktree = "path\to\other\worktree"  # Update this path

foreach ($file in $files) {
    Copy-Item $file -Destination $targetWorktree -Force
}
```

### 2. Clean Up Old Virtual Environments

```powershell
# In each worktree
Remove-Item -Recurse -Force .venv, venv -ErrorAction SilentlyContinue
```

### 3. Initialize UV

```powershell
# In each worktree
uv sync
```

This will:
- Create a new `.venv` virtual environment
- Install all dependencies from `pyproject.toml` using the locked versions from `uv.lock`
- Ensure consistency across all worktrees

### 4. Update Scripts

Replace `pip install` commands with `uv sync` in these files:

#### `start-backend.ps1`
Replace:
```powershell
pip install -r requirements.txt
```
With:
```powershell
uv sync
```

#### `backend/install_test_deps.ps1`
Replace:
```powershell
pip install pytest pytest-asyncio pytest-cov
```
With:
```powershell
uv sync --group dev
```

#### Any CI/CD workflows
Update `.github/workflows/*.yml` files to use `uv` instead of `pip`

### 5. Verify Installation

```powershell
# Check Python environment
uv run python --version

# Check installed packages
uv pip list

# Run your application
uv run python -m backend.app.main
# OR
uv run uvicorn backend.app.main:app --reload
```

### 6. Clean Up (Optional)

Once everything works, remove these files:
```powershell
Remove-Item backend/requirements.txt, backend/requirements_freeze.txt, requieremnts_frozen.txt, requieremnts_frozen_clean.txt, compare_deps.py -ErrorAction SilentlyContinue
```

## Common Issues

### Issue: "Access is denied" error
**Solution**: Kill all Python processes and retry:
```powershell
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
uv sync
```

### Issue: Package version conflicts
**Solution**: The `uv.lock` file has already resolved all conflicts. Just make sure you copied it correctly.

### Issue: Different Python version
**Solution**: UV will use the Python version specified in `.python-version` (3.10.11). Make sure you have it installed.

## Benefits of Using UV

1. **Faster**: 10-100x faster than pip
2. **Deterministic**: Lock file ensures everyone has the exact same versions
3. **Monorepo friendly**: Single `pyproject.toml` for all worktrees
4. **Better conflict resolution**: Handles complex dependency trees automatically
5. **No requirements.txt**: Everything in `pyproject.toml`

## Daily Workflow

### Add a new package
```powershell
uv add package-name
```

### Remove a package
```powershell
uv remove package-name
```

### Update packages
```powershell
uv sync --upgrade
```

### Run Python scripts
```powershell
uv run python script.py
```

### Activate virtual environment (if needed)
```powershell
.\.venv\Scripts\Activate.ps1
```
