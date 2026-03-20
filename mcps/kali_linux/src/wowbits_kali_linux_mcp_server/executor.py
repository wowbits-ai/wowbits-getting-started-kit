"""
executor.py — Command executor for the Kali MCP server.

Handles subprocess execution with timeouts, logging, and an optional
command allowlist (if ENFORCE_ALLOWLIST=true in the container env).
"""

import logging
import os
import shlex
import subprocess

logger = logging.getLogger(__name__)

# Pre-approved base commands. Enforced only when ENFORCE_ALLOWLIST=true.
ALLOWED_COMMANDS = {
    # Network recon
    "nmap", "netexec", "nxc",
    # Web
    "gobuster", "nikto", "sqlmap", "curl", "wget",
    # Exploitation helpers
    "searchsploit",
    # System / file utils (useful for agents navigating the container)
    "cat", "ls", "pwd", "find", "file", "stat", "head", "tail",
    "grep", "awk", "sed", "cut", "wc", "sort", "uniq", "tr",
    "echo", "printf", "env",
    # Network utils
    "ping", "traceroute", "ip", "ifconfig", "netstat", "ss",
    "whois", "dig", "host", "nslookup",
    # Scripting
    "python3", "python", "bash", "sh",
    # File transfers
    "scp", "rsync", "nc", "netcat",
}


def is_allowed(command: str) -> bool:
    """Return True if the base command is in the allowlist."""
    try:
        parts = shlex.split(command.strip())
        if not parts:
            return False
        base = os.path.basename(parts[0])
        return base in ALLOWED_COMMANDS
    except Exception:
        return False


def execute_tool(command: str, timeout: int = 120) -> str:
    """
    Execute a shell command locally inside the Kali container.

    Returns a formatted string containing stdout, stderr, and exit code.
    Never raises — errors are captured and returned in the string.
    """
    if not command or not command.strip():
        return "[ERROR] Empty command provided."

    enforce_allowlist = os.getenv("ENFORCE_ALLOWLIST", "false").lower() == "true"
    if enforce_allowlist and not is_allowed(command):
        base = shlex.split(command.strip())[0] if shlex.split(command.strip()) else "N/A"
        logger.warning("Blocked disallowed command: %s", base)
        return f"[ERROR] Command not in allowlist: {base}"

    logger.info("Executing (timeout=%ss): %s", timeout, command)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        rc = result.returncode
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        logger.debug("Exit %s for: %s", rc, command)
    except subprocess.TimeoutExpired:
        logger.warning("Timeout (%ss) for: %s", timeout, command)
        return f"[ERROR] Command timed out after {timeout} seconds."
    except Exception as exc:
        logger.error("Execution error for '%s': %s", command, exc)
        return f"[ERROR] Execution error: {exc}"

    parts = []
    if stdout:
        parts.append(stdout)
    if stderr:
        parts.append(f"[stderr]\n{stderr}")
    if rc not in (0, None) and not stderr:
        parts.append(f"[exit code: {rc}]")

    return "\n".join(parts) if parts else "Command completed with no output."
