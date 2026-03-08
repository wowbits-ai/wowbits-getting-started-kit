import subprocess
import sys
import shutil

# The default sandbox image used by llm-sandbox for Python execution.
# Pull this so the first run doesn't stall waiting for a large image download.
DOCKER_IMAGE = "vndee/sandbox-python-311-bullseye:latest"


def install():
    print("Installing llm-sandbox with MCP (Docker backend) support...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "llm-sandbox[mcp-docker]"]
        )
        print("llm-sandbox installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing llm-sandbox: {e}")
        sys.exit(1)

    # Pull the Docker sandbox image so it is ready for use.
    if shutil.which("docker") is None:
        print(
            "WARNING: 'docker' was not found in PATH. "
            "Please install Docker and ensure it is running before starting the MCP server."
        )
        return

    print(f"Pulling Docker sandbox image: {DOCKER_IMAGE} ...")
    try:
        subprocess.check_call(["docker", "pull", DOCKER_IMAGE])
        print("Docker image pulled successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error pulling Docker image: {e}")
        print(
            "The MCP server may still work if the image is already cached locally, "
            "but first-run code execution will fail without it."
        )


if __name__ == "__main__":
    install()
