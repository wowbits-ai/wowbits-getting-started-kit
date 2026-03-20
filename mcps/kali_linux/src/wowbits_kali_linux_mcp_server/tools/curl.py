"""
tools/curl.py — HTTP request tool.

Useful for interacting with web applications, APIs, login forms,
and crafting custom HTTP requests directly from an agent.
"""

import executor


def register(mcp) -> None:

    @mcp.tool()
    def curl_request(
        url: str,
        method: str = "GET",
        headers: str = "",
        data: str = "",
        cookies: str = "",
        follow_redirects: bool = True,
        insecure: bool = False,
        options: str = "",
        timeout: int = 30,
    ) -> str:
        """
        Make an HTTP request using curl and return the response.

        Args:
            url:              Target URL (e.g. 'http://10.10.10.1/login').
            method:           HTTP method: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS.
            headers:          Comma-separated headers to include
                              (e.g. 'Content-Type: application/json, Authorization: Bearer token').
            data:             Request body (for POST/PUT/PATCH).
                              Use JSON strings directly: '{"user":"admin","pass":"password"}'.
            cookies:          Cookie string (e.g. 'session=abc123; csrf=xyz').
            follow_redirects: Follow HTTP redirects (default True, adds -L flag).
            insecure:         Skip SSL certificate verification (default False, adds -k flag).
            options:          Any additional curl flags (e.g. '-v'  '--proxy http://127.0.0.1:8080').
            timeout:          Seconds before killed (default 30).
        """
        cmd = f"curl -s -X {method.upper()}"

        if follow_redirects:
            cmd += " -L"
        if insecure:
            cmd += " -k"

        # Add headers
        if headers:
            for h in headers.split(","):
                h = h.strip()
                if h:
                    cmd += f" -H '{h}'"

        # Add cookies
        if cookies:
            cmd += f" --cookie '{cookies}'"

        # Request body
        if data:
            cmd += f" -d '{data}'"

        if options:
            cmd += f" {options}"

        cmd += f" '{url}'"
        return executor.execute_tool(cmd, timeout=timeout)
