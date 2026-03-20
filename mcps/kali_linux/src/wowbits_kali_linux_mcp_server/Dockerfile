FROM kalilinux/kali-rolling:latest

# Install system tools and Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nmap \
    netexec \
    gobuster \
    nikto \
    sqlmap \
    exploitdb \
    wordlists \
    curl \
    wget \
    net-tools \
    dnsutils \
    whois \
    git \
    libcap2-bin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Unzip rockyou wordlist for convenience
RUN gunzip /usr/share/wordlists/rockyou.txt.gz 2>/dev/null || true

# Give nmap raw-socket capabilities so it works without full root
RUN setcap cap_net_raw,cap_net_admin+eip /usr/bin/nmap

# Install fastmcp
# Note: pip install dependencies
RUN pip3 install --break-system-packages fastmcp

# Create a working directory for file outputs (wget, etc.)
RUN mkdir -p /app/data

WORKDIR /app

# Copy the server, executor, and tools directory
COPY server.py /app/server.py
COPY executor.py /app/executor.py
COPY tools/ /app/tools/

ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8765
# Set to "true" to restrict execution to the pre-approved command allowlist
ENV ENFORCE_ALLOWLIST=false

# Expose the single MCP server port
EXPOSE 8765

CMD ["python3", "/app/server.py"]
