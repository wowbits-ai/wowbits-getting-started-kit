"""
tools/searchsploit.py — Exploit-DB search via searchsploit.

Helps agents find known exploits for a given technology, version, or CVE.
"""

import executor


def register(mcp) -> None:

    @mcp.tool()
    def searchsploit_query(
        search_term: str,
        exact_match: bool = False,
        options: str = "",
        timeout: int = 30,
    ) -> str:
        """
        Search the Exploit-DB database for exploits, shellcode, and papers.

        Args:
            search_term:  Keywords to search for.
                          Examples: 'apache 2.4'   'windows smb'   'CVE-2021-44228'
                                    'wordpress 5.8'   'vsftpd 2.3.4'
            exact_match:  Perform an exact title match with -e flag (default False).
            options:      Extra searchsploit flags:
                          '-w'       → show ExploitDB web URLs
                          '--json'   → JSON output
                          '--examine <EDB-ID>' → print exploit code
                          '--id'     → show only EDB-IDs
            timeout:      Seconds before killed (default 30).
        """
        cmd = f"searchsploit {search_term}"
        if exact_match:
            cmd += " -e"
        if options:
            cmd += f" {options}"
        return executor.execute_tool(cmd, timeout=timeout)
