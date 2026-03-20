"""
tools/nikto.py — Web vulnerability scanner.

nikto checks for dangerous files/CGIs, outdated software versions,
and server configuration issues.
"""

import executor


def register(mcp) -> None:

    @mcp.tool()
    def nikto_scan(
        target: str,
        port: str = "80",
        ssl: bool = False,
        options: str = "",
        timeout: int = 600,
    ) -> str:
        """
        Scan a web server for known vulnerabilities, misconfigurations, and outdated software.

        Args:
            target:  Target hostname or IP address (e.g. '10.10.10.1').
            port:    Target port (default 80; use 443 with ssl=True for HTTPS).
            ssl:     Set True to enable HTTPS/SSL scanning (-ssl flag).
            options: Extra nikto flags (e.g. '-Tuning 1234'  '-id admin:admin').
            timeout: Seconds before killed (default 600).
        """
        cmd = f"nikto -h {target} -p {port}"
        if ssl:
            cmd += " -ssl"
        if options:
            cmd += f" {options}"
        return executor.execute_tool(cmd, timeout=timeout)
