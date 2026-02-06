from app.core.app_settings import get_app_settings
from pathlib import Path

settings = get_app_settings()
print(f"Projects Database (raw): {settings.projects_database}")

db_path = settings.projects_database
if db_path and not db_path.is_absolute():
    repo_root = Path(__file__).resolve().parent
    db_path = (repo_root / db_path).resolve()
    print(f"Projects Database (resolved): {db_path}")
else:
    print(f"Projects Database (absolute): {db_path}")

print(f"WAF Feature Normalized: {settings.aaa_feature_waf_normalized}")
