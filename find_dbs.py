import os
from pathlib import Path
from datetime import datetime

root = Path("C:/Users/cyril.beurier/code")
for path in root.rglob("projects.db"):
    if "node_modules" in str(path):
        continue
    try:
        stat = path.stat()
        print(f"{path} | {stat.st_size} bytes | {datetime.fromtimestamp(stat.st_mtime)}")
    except Exception:
        pass
