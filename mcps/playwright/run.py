import subprocess
import os

# Get the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

# Ensure the subprocess runs in the correct directory
subprocess.run(['npx', '-y', '@playwright/mcp@latest', '--config', CONFIG_PATH], cwd=BASE_DIR)