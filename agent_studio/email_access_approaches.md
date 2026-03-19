## Email access integration approaches (options + trade-offs)

This project supports **Connectors** as the way to supply credentials/config to tools at runtime (stored in DB). The email tool should read a connector’s `config` rather than environment variables.

### Approach A (recommended for Gmail): Gmail API + OAuth (refresh token)

- **How it works**: user completes a one-time OAuth consent. You store `client_id`, `client_secret`, and `refresh_token` in a connector config. The tool refreshes an access token automatically when it runs.
- **Pros**: best Gmail metadata, label/thread support, reliable search queries, secure (scoped OAuth).
- **Cons**: you must implement or run an OAuth consent flow once to obtain the refresh token.
- **Best for**: individual Gmail accounts and “daily summary of my inbox”.
- **Connector config** (example):
  - `client_id`, `client_secret`, `refresh_token`, optional `scopes`
- **Scopes**:
  - Read-only: `https://www.googleapis.com/auth/gmail.readonly`
  - More access (avoid unless needed): `https://www.googleapis.com/auth/gmail.modify`

### Approach B (recommended for organizations): Google Workspace Service Account + Domain-Wide Delegation

- **How it works**: an admin enables Domain-Wide Delegation for a Google Workspace domain, authorizes a service account for Gmail scopes, and the tool impersonates users (sets `subject`).
- **Pros**: centralized admin setup, no per-user OAuth, works across mailboxes at scale.
- **Cons**: admin/security process; more complex setup; not available for consumer Gmail.
- **Best for**: company-wide daily summaries, shared mailboxes, compliance-managed environments.
- **Connector config** (example):
  - service account JSON, `delegated_user` / `subject`, scopes

### Approach C (generic fallback): IMAP

- **How it works**: connect via IMAP using host/port + username/password (often app-password) or OAuth2 SASL (provider-dependent).
- **Pros**: works with many providers (Gmail/Outlook/Yahoo/custom domains).
- **Cons**: fewer structured features than native APIs; provider security restrictions; throttling; Gmail “less secure app” is not allowed (must use OAuth2 or app passwords).
- **Best for**: “any email provider” support, quick prototypes, when APIs aren’t available.
- **Connector config** (example):
  - `host`, `port`, `username`, `password` (secret) OR OAuth2 fields

### Approach D (for Outlook/Microsoft 365): Microsoft Graph

- **How it works**: register an Azure AD app; use delegated OAuth (per user) or application permissions (admin consent). Fetch mail via Graph endpoints.
- **Pros**: first-class for Outlook/M365, rich metadata, enterprise friendly.
- **Cons**: Azure setup; tokens/consent management.
- **Best for**: Microsoft 365 tenants, enterprise deployments.
- **Connector config** (example):
  - delegated: `client_id`, `client_secret`, `refresh_token`, `tenant_id`
  - app perms: `client_id`, `client_secret`, `tenant_id`, mailbox to access

### Approach E (unified third-party providers): Nylas / etc.

- **How it works**: integrate a single API that supports multiple email providers; store the third-party access token in a connector config.
- **Pros**: fastest multi-provider support; fewer provider-specific edge cases.
- **Cons**: vendor dependency, cost, privacy considerations.
- **Best for**: productizing a multi-provider email agent quickly.

### Practical recommendation for this repo

For your current requirement (“summary of all email in one day”):
- Start with **Approach A (Gmail OAuth refresh token)** and a connector named (for example) `gmail`.
- Later add:
  - **Microsoft Graph** connector for Outlook users, or
  - **IMAP** connector as a generic fallback.

