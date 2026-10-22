#!/usr/bin/env bash
# Assemble an immutable GitHub Release snapshot without rebuilding unchanged mods.
# Usage: release_snapshot.sh <dist-directory> <owned-asset-glob>...
# All other current release assets are taken byte-for-byte from GitHub's Latest
# immutable Release. This script does not create, delete or modify a Release.
set -euo pipefail

fail() { printf 'Release snapshot blocked: %s\n' "$*" >&2; exit 1; }
[[ $# -ge 2 ]] || fail 'Expected DIST and at least one owned-asset glob'
dest="$(realpath -- "$1")"
shift
[[ -d "$dest" && -f "$dest/SHA256SUMS.txt" ]] || fail 'Missing locally verified build/manifest'
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
(cd "$dest" && sha256sum --check --strict SHA256SUMS.txt) || fail 'Local build checksum failed'

# The Latest marker is repository-wide and updated by every mod publisher.
# Only immutable published Releases are permitted as a source for carry-forward.
releases="$(gh release list --repo "$GITHUB_REPOSITORY" --limit 200 \
  --json tagName,isDraft,isPrerelease,isLatest,isImmutable)" || fail 'Cannot list published Releases'
published_count="$(jq -r '[.[] | select(.isDraft == false and .isPrerelease == false)] | length' <<< "$releases")"
latest="$(jq -r '[.[] | select(.isLatest == true and .isDraft == false and .isPrerelease == false)] |
  if length == 0 then "" elif length == 1 then .[0].tagName else "DUPLICATE" end' <<< "$releases")"
[[ "$latest" != DUPLICATE ]] || fail 'More than one Latest release'
if [[ -z "$latest" ]]; then
  [[ "$published_count" == 0 ]] || fail 'Published Releases exist, but none is marked Latest'
else
  immutable="$(jq -r --arg tag "$latest" '.[] | select(.tagName == $tag) | .isImmutable' <<< "$releases")"
  [[ "$immutable" == true ]] || fail "Latest Release $latest is not immutable"
  staging="$(mktemp -d)"
  trap 'rm -rf -- "$staging"' EXIT
  gh release download "$latest" --repo "$GITHUB_REPOSITORY" --dir "$staging" || fail 'Cannot download previous Release'
  [[ -f "$staging/SHA256SUMS.txt" ]] || fail 'Previous Release lacks checksum manifest'
  # Confirm that every downloaded asset is listed and that every listed hash
  # matches its bytes. No unchecked extra asset can be carried to a new Release.
  expected="$(sed -nE 's/^[0-9a-f]{64}  ([A-Za-z0-9][A-Za-z0-9._-]*)$/\1/p' "$staging/SHA256SUMS.txt" | LC_ALL=C sort)"
  actual="$(find "$staging" -mindepth 1 -maxdepth 1 -type f ! -name SHA256SUMS.txt -printf '%f\n' | LC_ALL=C sort)"
  [[ -n "$actual" && "$expected" == "$actual" ]] || fail 'Previous Release has missing, unsafe or unlisted assets'
  (cd "$staging" && sha256sum --check --strict SHA256SUMS.txt) || fail 'Previous Release failed SHA-256 verification'
  while IFS= read -r name; do
    own=false
    for pattern in "$@"; do
      # shellcheck disable=SC2053
      if [[ "$name" == $pattern ]]; then own=true; break; fi
    done
    if [[ "$own" == true ]]; then
      printf 'Replace own previous asset: %s\n' "$name"
      continue
    fi
    [[ ! -e "$dest/$name" ]] || fail "Asset name conflict: $name"
    cp -- "$staging/$name" "$dest/$name"
    printf 'Carry immutable asset from %s: %s\n' "$latest" "$name"
  done <<< "$actual"
fi

# The new checksum manifest covers the entire snapshot (updated + unchanged).
# Each manifest is immutable once GitHub publishes the release.
(
  cd "$dest"
  rm -- SHA256SUMS.txt
  find . -mindepth 1 -maxdepth 1 -type f ! -name SHA256SUMS.txt -printf '%f\n' | LC_ALL=C sort |
    while IFS= read -r name; do
      [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || fail 'Unsafe output asset name'
      sha256sum -- "$name"
    done > SHA256SUMS.txt
  sha256sum --check --strict SHA256SUMS.txt
) || fail 'Assembled Release snapshot failed integrity verification'
