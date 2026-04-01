import subprocess

try:
    result = subprocess.run(["catt", "scan"], capture_output=True, text=True, timeout=10)
    print("STDOUT:", repr(result.stdout))
    print("STDERR:", repr(result.stderr))
except Exception as e:
    print("ERROR:", str(e))
