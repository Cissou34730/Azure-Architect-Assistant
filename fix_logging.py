
import re

path = 'backend/app/services/backfill_service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find logger.xyz("message", key=value, ...)
# This is a bit complex for a simple regex if multi-line, but let's try for single lines first
def fix_line(match):
    level = match.group(1)
    message = match.group(2)
    args_str = match.group(3)
    
    # Parse key=value pairs
    kwargs = re.findall(r'(\w+)=([^,]+)', args_str)
    if not kwargs:
        return match.group(0)
    
    formatted_args = ", ".join([f"{k}={{ {v.strip()} }}" for k, v in kwargs])
    # Standard logger doesn't support this naturally, so we'll just put them in the string
    new_message = f"{message}: {formatted_args}"
    return f'logger.{level}(f"{new_message}")'

# Basic fix for common patterns in this file
content = content.replace('logger.info("Backfill progress", processed=summary["processed"], total=summary["total_projects"])', 
                         'logger.info(f"Backfill progress: processed={summary[\'processed\']}, total={summary[\'total_projects\']}")')

content = content.replace('logger.warning("Verification failed", project_id=str(project_id), diffs=diffs)',
                         'logger.warning(f"Verification failed: project_id={project_id}, diffs={diffs}")')

content = content.replace('logger.exception("Backfill error", project_id=str(project_id))',
                         'logger.exception(f"Backfill error: project_id={project_id}")')

content = content.replace('logger.info("Backfill complete", summary=summary)',
                         'logger.info(f"Backfill complete: summary={summary}")')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixes applied to backfill_service.py")
