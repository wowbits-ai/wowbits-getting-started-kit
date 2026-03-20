"""
tools/gobuster.py — Directory, DNS, and vhost brute-forcing with gobuster.
"""

import executor

_DEFAULT_WORDLIST_DIR = "/usr/share/wordlists/dirb/common.txt"
_DEFAULT_WORDLIST_DNS = "/usr/share/wordlists/dirb/common.txt"


def register(mcp) -> None:

    @mcp.tool()
    def gobuster_dir(
        url: str,
        wordlist: str = _DEFAULT_WORDLIST_DIR,
        extensions: str = "",
        threads: int = 10,
        options: str = "",
        timeout: int = 300,
    ) -> str:
        """
        Brute-force web directories and files on a target URL.

        Args:
            url:        Target URL (e.g. 'http://10.10.10.1').
            wordlist:   Path to wordlist file inside container.
                        Default: /usr/share/wordlists/dirb/common.txt
                        Others:  /usr/share/wordlists/dirbuster/medium.txt
                                 /usr/share/seclists/Discovery/Web-Content/raft-medium-words.txt
            extensions: Comma-separated file extensions to check (e.g. 'php,html,txt,bak').
            threads:    Number of concurrent threads (default 10).
            options:    Extra gobuster dir flags (e.g. '-q --status-codes 200,301').
            timeout:    Seconds before killed (default 300).
        """
        cmd = f"gobuster dir -u {url} -w {wordlist} -t {threads}"
        if extensions:
            cmd += f" -x {extensions}"
        if options:
            cmd += f" {options}"
        return executor.execute_tool(cmd, timeout=timeout)

    @mcp.tool()
    def gobuster_dns(
        domain: str,
        wordlist: str = _DEFAULT_WORDLIST_DNS,
        threads: int = 10,
        options: str = "",
        timeout: int = 300,
    ) -> str:
        """
        Enumerate DNS subdomains for a target domain.

        Args:
            domain:   Target domain (e.g. 'example.com').
            wordlist: Path to wordlist file inside container.
            threads:  Number of concurrent threads (default 10).
            options:  Extra gobuster dns flags (e.g. '--wildcard').
            timeout:  Seconds before killed (default 300).
        """
        cmd = f"gobuster dns -d {domain} -w {wordlist} -t {threads}"
        if options:
            cmd += f" {options}"
        return executor.execute_tool(cmd, timeout=timeout)

    @mcp.tool()
    def gobuster_vhost(
        url: str,
        wordlist: str = _DEFAULT_WORDLIST_DIR,
        threads: int = 10,
        options: str = "",
        timeout: int = 300,
    ) -> str:
        """
        Brute-force virtual hostnames on a target web server.

        Args:
            url:      Target base URL (e.g. 'http://10.10.10.1').
            wordlist: Path to wordlist file inside container.
            threads:  Number of concurrent threads (default 10).
            options:  Extra gobuster vhost flags.
            timeout:  Seconds before killed (default 300).
        """
        cmd = f"gobuster vhost -u {url} -w {wordlist} -t {threads}"
        if options:
            cmd += f" {options}"
        return executor.execute_tool(cmd, timeout=timeout)
