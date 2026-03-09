import subprocess
import sys
import os
from pathlib import Path


def check_command(cmd, description):
    """Check if a command is available."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True
        )
        version = result.stdout.strip()
        print(f"  ✅ {description}: {version}")
        return True
    except FileNotFoundError:
        print(f"  ❌ {description}: NOT FOUND")
        return False


def main():
    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║     Memento Protocol MCP Server Setup (Local Clone)         ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    # Step 1: Verify prerequisites
    print("🔍 Checking prerequisites...\n")
    
    ok = True
    ok = check_command(["node", "--version"], "Node.js") and ok
    ok = check_command(["npm", "--version"], "npm") and ok
    ok = check_command(["git", "--version"], "Git") and ok

    if not ok:
        print("\n❌ Missing prerequisites. Please install Node.js and Git first.")
        print("   Node.js: https://nodejs.org/")
        print("   Git: https://git-scm.com/")
        sys.exit(1)

    # Step 2: Clone the memento-protocol repo if not already present
    mcp_dir = Path(__file__).resolve().parent
    repo_dir = mcp_dir / "memento-protocol"

    if repo_dir.exists() and (repo_dir / "package.json").exists():
        print(f"\n📁 Memento protocol repo already cloned at: {repo_dir}")
        print("  ✅ Skipping clone (already exists)")
        
        # Pull latest changes
        print("\n🔄 Pulling latest changes...")
        result = subprocess.run(
            ["git", "pull"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  ✅ {result.stdout.strip()}")
        else:
            print(f"  ⚠️  Git pull failed: {result.stderr.strip()}")
    else:
        print(f"\n📥 Cloning memento-protocol repo...")
        result = subprocess.run(
            [
                "git", "clone",
                "https://github.com/myrakrusemark/memento-protocol.git",
                str(repo_dir),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  ❌ Clone failed: {result.stderr.strip()}")
            sys.exit(1)
        print(f"  ✅ Cloned to {repo_dir}")

    # Step 3: Install npm dependencies
    print("\n📦 Installing npm dependencies...")
    result = subprocess.run(
        ["npm", "install"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ❌ npm install failed: {result.stderr.strip()}")
        sys.exit(1)
    print("  ✅ npm dependencies installed")

    # Step 4: Verify supergateway is available
    print("\n🔧 Verifying supergateway availability...")
    result = subprocess.run(
        ["npx", "-y", "supergateway", "--help"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("  ✅ supergateway is available via npx")
    else:
        print("  ⚠️  supergateway will be auto-installed on first run via npx -y")


if __name__ == "__main__":
    main()
