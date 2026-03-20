import subprocess
import json
import os
import sys

# Get the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Always use the current Python interpreter so this works across environments
# regardless of any absolute path stored in config.json.
args = config.get('args', [])
env_overrides = config.get('env', {})

# Merge with the current environment so system paths remain intact
env = os.environ.copy()
env.update(env_overrides)

print(f"Starting llm-sandbox MCP server with {sys.executable} {' '.join(args)}")
subprocess.run([sys.executable] + args, env=env, cwd=BASE_DIR)
