# Public repository: privacy and provenance

The repo is now **public**. The build-time privacy scanner checks source, release resources, notes and common secret formats, but it does not scan Git commit metadata or GitHub Actions/PR records.

- **GitHub commit author/committer names and platform PR/review history are public.** They may contain personal attribution from earlier commits. Changing a profile display name does not change already-published commit objects or cached PR activities. Check this separately before distributing project links.
- Do not commit `staysharp.log`, `python.log`, screenshots, game identifiers, private account exports, credentials or user-machine paths.
- Run `python3 scripts/privacy_audit.py` and tests for every reviewed PR.
- The DDS master is an image file without EXIF/user metadata; the resulting `.wotmod` includes the runtime bootstrap and 21 DDS frames only.
- No network telemetry or secrets are used by the mod. Its diagnostic log remains local and is never uploaded by the mod itself.
- A public repository is **not** the same as a privacy guarantee. Review Git history, Release notes, Actions logs and GitHub-account attribution manually.
- Consider choosing a source license via a separate reviewed change; public visibility does not automatically grant reuse permissions.
