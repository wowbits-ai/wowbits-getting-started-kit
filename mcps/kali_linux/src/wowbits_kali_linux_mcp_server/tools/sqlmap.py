"""
tools/sqlmap.py — Automated SQL injection detection and exploitation.
"""

import executor


def register(mcp) -> None:

    @mcp.tool()
    def sqlmap_test(
        url: str,
        parameter: str = "",
        data: str = "",
        technique: str = "",
        level: int = 1,
        risk: int = 1,
        dbms: str = "",
        options: str = "",
        timeout: int = 600,
    ) -> str:
        """
        Test a URL for SQL injection vulnerabilities using sqlmap.

        Args:
            url:        Target URL (e.g. 'http://10.10.10.1/page?id=1').
            parameter:  Specific GET/POST parameter to test (e.g. 'id').
            data:       POST data string (e.g. 'user=foo&pass=bar').
            technique:  SQLi techniques to try — any combo of letters:
                        B(oolean) E(rror) U(nion) S(tacked) T(ime) Q(uery).
                        Default: all.
            level:      Test depth 1-5 (more payloads at higher levels; default 1).
            risk:       Risk of tests 1-3 (potentially destructive at higher risk; default 1).
            dbms:       Force a specific DBMS (e.g. 'mysql', 'mssql', 'postgresql').
            options:    Extra sqlmap flags (e.g. '--dbs'  '--dump'  '--tables  -D dbname').
            timeout:    Seconds before killed (default 600).
        """
        cmd = (
            f"sqlmap -u '{url}' --batch --random-agent "
            f"--level {level} --risk {risk}"
        )
        if parameter:
            cmd += f" -p {parameter}"
        if data:
            cmd += f" --data='{data}'"
        if technique:
            cmd += f" --technique={technique}"
        if dbms:
            cmd += f" --dbms={dbms}"
        if options:
            cmd += f" {options}"
        return executor.execute_tool(cmd, timeout=timeout)
