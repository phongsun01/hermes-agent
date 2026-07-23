import os
import sys
import shutil
from datetime import datetime

# Enforce UTF-8 encoding for standard output on Windows command prompt
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def safe_write(file_path: str, new_content: str, force: bool = False):
    # Ensure directory exists
    dir_name = os.path.dirname(file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    # If file doesn't exist, write directly
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"SUCCESS: Created new file at {file_path}")
        return True

    # Read existing content
    with open(file_path, 'r', encoding='utf-8') as f:
        old_content = f.read()

    # Calculate metrics
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    # Integrity Check: If new content is significantly shorter
    if len(old_lines) > 5 and len(new_lines) < len(old_lines) * 0.5:
        if not force:
            print("WARNING: New content is significantly shorter (less than 50% of the lines) than the existing content.")
            print(f"Old file: {len(old_lines)} lines, New content: {len(new_lines)} lines.")
            print("This operation was blocked to prevent data loss. Use --force to override.")
            return False

    # Create backup
    # Find or create .obsidian/hermes-backups folder in the vault root
    # We resolve vault root by searching upwards or finding .obsidian folder
    vault_root = dir_name
    while vault_root and not os.path.exists(os.path.join(vault_root, ".obsidian")):
        parent = os.path.dirname(vault_root)
        if parent == vault_root: # reached system root
            break
        vault_root = parent

    backup_dir = os.path.join(vault_root, ".obsidian", "hermes-backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.basename(file_path)
    backup_path = os.path.join(backup_dir, f"{file_name}.{timestamp}.bak")

    shutil.copy2(file_path, backup_path)
    
    # Write new content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"SUCCESS: Overwrote file at {file_path}")
    print(f"Backup created at: {backup_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python safe_write.py <file_path> <content> [--force]")
        sys.exit(1)
        
    path = sys.argv[1]
    content = sys.argv[2]
    force_write = "--force" in sys.argv
    
    success = safe_write(path, content, force_write)
    if not success:
        sys.exit(2)
