"""
tools/wget.py — File download and web spidering.
"""

import executor

_DATA_DIR = "/app/data"


def register(mcp) -> None:

    @mcp.tool()
    def wget_download(
        url: str,
        output_filename: str = "",
        spider: bool = False,
        recursive: bool = False,
        insecure: bool = False,
        options: str = "",
        timeout: int = 120,
    ) -> str:
        """
        Download a file or spider a website using wget.

        Downloaded files are saved in /app/data inside the container,
        which is mounted to ./data on the host.

        Args:
            url:             URL to download (e.g. 'http://10.10.10.1/shell.php').
            output_filename: Save the file as this name inside /app/data.
                             Leave empty to use the remote filename.
            spider:          Check whether a URL exists without downloading (--spider).
            recursive:       Recursively download linked pages (-r -l 2).
            insecure:        Skip SSL certificate check (--no-check-certificate).
            options:         Extra wget flags (e.g. '-q'  '--user=admin --password=pass').
            timeout:         Seconds before killed (default 120).
        """
        cmd = "wget"

        if spider:
            cmd += " --spider"
        elif output_filename:
            cmd += f" -O {_DATA_DIR}/{output_filename}"
        else:
            cmd += f" -P {_DATA_DIR}"

        if recursive:
            cmd += " -r -l 2"
        if insecure:
            cmd += " --no-check-certificate"
        if options:
            cmd += f" {options}"

        cmd += f" '{url}'"
        return executor.execute_tool(cmd, timeout=timeout)
