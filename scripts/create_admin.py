"""Create the first administrator interactively:  python scripts/create_admin.py
Thin wrapper around:  flask --app run create-admin"""
import os
import subprocess
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
subprocess.run([sys.executable, "-m", "flask", "--app", "run", "init-db"], cwd=root, check=True)
subprocess.run([sys.executable, "-m", "flask", "--app", "run", "create-admin"], cwd=root, check=True)
