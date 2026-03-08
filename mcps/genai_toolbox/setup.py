import subprocess
import sys

def setup():
    """Install GenAI Toolbox for Databases via Homebrew."""
    print("Installing GenAI Toolbox for Databases...")
    try:
        # Try Homebrew first (macOS/Linux)
        result = subprocess.run(['brew', 'install', 'mcp-toolbox'], capture_output=True, text=True)
        if result.returncode == 0:
            print("GenAI Toolbox installed successfully via Homebrew.")
            return
        else:
            print(f"Homebrew install failed: {result.stderr}")
    except FileNotFoundError:
        print("Homebrew not found.")

    # Fallback: download binary directly (macOS Apple Silicon)
    print("Attempting direct binary download...")
    try:
        version = "0.27.0"
        url = f"https://storage.googleapis.com/genai-toolbox/v{version}/darwin/arm64/toolbox"
        subprocess.run(['curl', '-L', '-o', '/usr/local/bin/toolbox', url], check=True)
        subprocess.run(['chmod', '+x', '/usr/local/bin/toolbox'], check=True)
        print(f"GenAI Toolbox v{version} installed successfully.")
    except Exception as e:
        print(f"Failed to install GenAI Toolbox: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup()
