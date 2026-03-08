import subprocess
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
tools_file = os.path.join(script_dir, 'tools.yaml')

# Run the GenAI Toolbox server with the tools.yaml configuration
subprocess.run([
    'toolbox',
    '--tools-file', tools_file,
    '--port', '5050',
    '--address', '127.0.0.1'
])
