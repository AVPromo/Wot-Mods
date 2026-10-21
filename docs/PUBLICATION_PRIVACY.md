# Pre-publication privacy checklist

The tracked code and package were audited for accidental personal or security-related information. No identity/nickname, player ID, device ID, Windows user profile, email address, tokens or keys were found. The DDS source contains image data only; there is no EXIF or author block. The runtime log is created **locally** on the player's PC, not included in Git.

Checklist before making the repository public:

- Review **all PR files**, including `.github/workflows`, and Actions output. GitHub makes historic **Actions logs and history public** when repository visibility switches to public.
- Review commit author/committer details and the GitHub account username. These are part of the project's public provenance, and **cannot be anonymized by the mod's code**.
- Confirm no `.env`, workflow secrets, `python.log`, `staysharp.log`, `*.dmp`, screenshots of game accounts, local config exports or archives have ever been committed.
- Review issue/PR descriptions and review comments: those also become public with the repo.
- Run `python3 scripts/privacy_audit.py` and build tests before each merge.
- Decide whether to add an open-source `LICENSE`. Publicly readable source does not automatically grant a software license.

The security scanner is a **defense in depth** measure, not a guarantee. It catches common formats, not all possible sensitive or personal data. The source contains generic `%LOCALAPPDATA%` only, not an actual username or home path. No runtime HTTP requests, third-party telemetry, or sound assets are used.
