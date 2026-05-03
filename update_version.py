import os
import re

# Read version from backend/version.py
version_file = "backend/version.py"
with open(version_file, "r", encoding="utf-8") as f:
    content = f.read()
    version_match = re.search(r'VERSION = "([^"]+)"', content)
    if not version_match:
        print("Could not find VERSION in backend/version.py")
        exit(1)
    VERSION = version_match.group(1)

print(f"Updating all files to version V{VERSION}...")

def update_file(file_path, pattern, replacement):
    if not os.path.exists(file_path):
        print(f"File {file_path} not found, skipping.")
        return
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")

# Update README.md title
update_file("README.md", r"# Lumina Képtár \(V[0-9.]+\)", f"# Lumina Képtár (V{VERSION})")

# Update verziokontroll.md title (optional, usually history is static)
# But we can update the header if there is one.

print("Done. Dynamic pages and API already use the centralized variable.")
