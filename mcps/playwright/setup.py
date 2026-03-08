import subprocess
import sys
import shutil

def install():
    print("Installing Playwright browsers...")
    # Check if npx is available
    if shutil.which('npx') is None:
        print("Error: 'npx' is not found in PATH. Please ensure Node.js and npm are installed.")
        sys.exit(1)
        
    try:
        subprocess.check_call(['npx', '-y', 'playwright', 'install'])
        print("Playwright browsers installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing Playwright browsers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install()
