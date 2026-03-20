"""
tools/terminal.py — Generic raw terminal execution.

The most flexible tool: runs any arbitrary shell command on the
Kali container and returns its output.  Use dedicated tools first
(nmap, gobuster, etc.) and fall back to this for everything else.
"""

import executor


def register(mcp) -> None:

    @mcp.tool()
    def run_terminal_command(command: str, timeout: int = 120) -> str:
        """
        Run any shell command on the Kali Linux container and return its output.

        Use this for commands not covered by the dedicated tools
        (e.g. 'cat /etc/passwd', 'python3 exploit.py', 'netcat -lvp 4444').

        Args:
            command: Full shell command to execute (e.g. 'ls -la /tmp').
            timeout: Maximum seconds to wait before the command is killed (default 120).
        """
        return executor.execute_tool(command, timeout=timeout)
