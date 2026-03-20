"""
tools/nxc.py — NetExec (nxc) network exploitation.

NetExec is the community continuation of CrackMapExec.
Supports SMB, SSH, WinRM, RDP, LDAP, MSSQL, FTP and more.
"""

import executor

_VALID_PROTOCOLS = {"smb", "ssh", "winrm", "rdp", "ldap", "ldaps", "mssql", "ftp", "vnc", "wmi"}


def register(mcp) -> None:

    @mcp.tool()
    def nxc_smb(
        target: str,
        username: str = "",
        password: str = "",
        domain: str = "",
        options: str = "",
        timeout: int = 120,
    ) -> str:
        """
        Run NetExec (nxc) against SMB to enumerate shares, check credentials, list users/groups.

        Args:
            target:   Target IP, hostname, or CIDR range (e.g. '10.10.10.1').
            username: Username for authentication (optional).
            password: Password for authentication (optional).
            domain:   Windows domain name (optional).
            options:  Extra nxc flags.
                      Examples: '--shares'  '--users'  '--groups'  '--pass-pol'
                                '--rid-brute'  '--sam'  '--lsa'  '-x "whoami"'
            timeout:  Seconds before the command is killed (default 120).
        """
        cmd = f"nxc smb {target}"
        if username:
            cmd += f" -u '{username}'"
        if password:
            cmd += f" -p '{password}'"
        if domain:
            cmd += f" -d '{domain}'"
        if options:
            cmd += f" {options}"
        return executor.execute_tool(cmd, timeout=timeout)

    @mcp.tool()
    def nxc_run(
        protocol: str,
        target: str,
        options: str = "",
        timeout: int = 120,
    ) -> str:
        """
        Run NetExec (nxc) against any supported protocol.

        Args:
            protocol: Target protocol — one of: smb, ssh, winrm, rdp, ldap, mssql, ftp, vnc, wmi.
            target:   Target IP, hostname, or CIDR range.
            options:  Full nxc option string (e.g. '-u admin -p pass --shares').
            timeout:  Seconds before the command is killed (default 120).
        """
        cmd = f"nxc {protocol} {target} {options}"
        return executor.execute_tool(cmd, timeout=timeout)
