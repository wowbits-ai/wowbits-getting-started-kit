"""
tools/nmap.py — Network scanner.

Wraps nmap with typed parameters so agents don't have to remember flags.
Falls through to run_terminal_command for anything more exotic.
"""

import executor

_SCAN_FLAGS = {
    "basic":      "-sT",           # TCP connect — no root needed
    "stealth":    "-sS",           # SYN scan — needs NET_RAW cap
    "udp":        "-sU",           # UDP scan
    "version":    "-sV",           # Service/version detection
    "os":         "-O",            # OS fingerprinting
    "aggressive": "-A",            # OS + version + scripts + traceroute
    "vuln":       "-sV --script vuln",   # Run vuln NSE scripts
    "full":       "-p- -sS -sV -O",     # All ports, SYN, version, OS
}


def register(mcp) -> None:

    @mcp.tool()
    def nmap_scan(
        target: str,
        scan_type: str = "basic",
        ports: str = "",
        extra_flags: str = "",
        timeout: int = 300,
    ) -> str:
        """
        Run an nmap network scan against a target host or range.

        Args:
            target:      IP address, hostname, or CIDR range
                         (e.g. '10.10.10.1' or '192.168.1.0/24').
            scan_type:   One of: basic, stealth, udp, version, os, aggressive, vuln, full.
                         default is 'basic' (TCP connect scan, no special privileges needed).
            ports:       Port specification to scan.  Leave empty for nmap defaults.
                         Examples: '22,80,443'  or  '1-65535'  or  'T:80,U:53'.
            extra_flags: Any additional nmap flags (e.g. '--script http-title -v').
            timeout:     Seconds before the scan is killed (default 300).
        """
        flags = _SCAN_FLAGS.get(scan_type, "-sT")
        cmd = f"nmap {flags} {target}"
        if ports:
            cmd += f" -p {ports}"
        if extra_flags:
            cmd += f" {extra_flags}"
        return executor.execute_tool(cmd, timeout=timeout)
