#!/usr/bin/env bash
# First-party GitHub Releases publisher. No REST client, network library or personal access token.
# GitHub Actions provides GH_TOKEN; gh release handles creation, asset uploads
# and publication. Git handles tag verification, sha256sum handles integrity.
set -Eeuo pipefail

fail() { printf 'Release blocked: %s\n' "$*" >&2; exit 1; }

: "${GITHUB_REPOSITORY:?GitHub repository must be set}"
: "${RELEASE_TAG:?Release tag must be set}"
: "${RELEASE_VERSION:?Release version must be set}"
: "${GH_TOKEN:?GitHub Actions GH_TOKEN must be set}"
RELEASE_COMMIT="${RELEASE_COMMIT:-${GITHUB_SHA:-}}"
DIST="${STAYSHARP_DIST_DIR:-dist}"
RECOVERY="${STAYSHARP_RECOVERY_MODE:-0}"

[[ "$RELEASE_VERSION" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || fail 'Invalid semantic version'
[[ "$RELEASE_TAG" == "v$RELEASE_VERSION" ]] || fail 'Tag and release version disagree'
[[ "$RELEASE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || fail 'Commit must be a 40-digit Git SHA'
[[ "$GITHUB_REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail 'Invalid repository name'
[[ "$RECOVERY" == 0 || "$RECOVERY" == 1 ]] || fail 'Invalid recovery mode'
for command_name in gh git jq sha256sum cmp mktemp; do
    command -v "$command_name" >/dev/null 2>&1 || fail "Missing required command: $command_name"
done

MOD_NAME="com.staysharp.medkitreminder_${RELEASE_VERSION}.wotmod"
MOD_FILE="$DIST/$MOD_NAME"
MANIFEST="$DIST/SHA256SUMS.txt"
[[ -f "$MOD_FILE" && -f "$MANIFEST" ]] || fail 'Built mod or checksum manifest is missing'
shopt -s nullglob
mods=("$DIST"/*.wotmod)
[[ "${#mods[@]}" == 1 && "${mods[0]}" == "$MOD_FILE" ]] || fail 'Dist has an unexpected number of mods'
expected_manifest="$(cd "$DIST" && sha256sum -- "$MOD_NAME")"
actual_manifest="$(cat "$MANIFEST")"
[[ "$actual_manifest" == "$expected_manifest" ]] || fail 'Manifest does not match local build'
(cd "$DIST" && sha256sum --check --status SHA256SUMS.txt) || fail 'Local SHA-256 verification failed'

# Compare the *peeled commit* for lightweight and annotated remote tags.
# Never move an existing tag or attach a differently built artifact to it.
remote_tag_commit() {
    local response sha ref direct='' peeled=''
    response="$(git ls-remote --tags origin "refs/tags/$RELEASE_TAG" "refs/tags/$RELEASE_TAG^{}")" || fail 'Cannot inspect remote Git tags'
    while IFS=$'\t' read -r sha ref; do
        [[ -z "$sha" ]] && continue
        case "$ref" in
            "refs/tags/$RELEASE_TAG") direct="$sha" ;;
            "refs/tags/$RELEASE_TAG^{}") peeled="$sha" ;;
            *) fail 'Unexpected remote tag response' ;;
        esac
    done <<< "$response"
    printf '%s' "${peeled:-$direct}"
}

existing_commit="$(remote_tag_commit)"
if [[ -n "$existing_commit" && "$existing_commit" != "$RELEASE_COMMIT" ]]; then
    fail "Tag $RELEASE_TAG belongs to $existing_commit, not $RELEASE_COMMIT"
fi
if [[ "$RECOVERY" == 1 && -z "$existing_commit" ]]; then
    fail 'Recovery requires an existing, correctly targeted Git tag'
fi

# GitHub CLI lists drafts as well as published releases. A draft cannot be
# reliably opened via the by-tag REST endpoint, so never infer its absence
# from `gh release view` returning HTTP 404.
release_list="$(gh release list --repo "$GITHUB_REPOSITORY" --json tagName,isDraft,isPrerelease --limit 5000)" || fail 'Cannot list GitHub releases'
match="$(printf '%s' "$release_list" | jq -c --arg tag "$RELEASE_TAG" '[.[] | select(.tagName == $tag)]')" || fail 'Invalid release listing'
match_count="$(printf '%s' "$match" | jq 'length')"
[[ "$match_count" -le 1 ]] || fail 'Duplicate releases use the same tag'
if [[ "$match_count" == 1 ]]; then
    draft="$(printf '%s' "$match" | jq -r '.[0].isDraft')"
    prerelease="$(printf '%s' "$match" | jq -r '.[0].isPrerelease')"
    [[ "$prerelease" == false ]] || fail 'Unexpected prerelease for this tag'
    case "$draft" in
        false)
            printf 'Release %s already published; checking immutable assets.\n' "$RELEASE_TAG"
            ;;
        true)
            if [[ "$RECOVERY" != 1 ]]; then
                fail "An interrupted draft $RELEASE_TAG exists. Use the Recovery workflow or remove the draft in GitHub Releases."
            fi
            printf 'Recovering interrupted draft %s using native gh release commands.\n' "$RELEASE_TAG"
            # Only a verified draft is eligible. Keep its Git tag: it still
            # points at exactly the source commit we rebuilt.
            if ! gh release delete "$RELEASE_TAG" --yes --repo "$GITHUB_REPOSITORY"; then
                fail "gh could not delete draft $RELEASE_TAG. Delete ONLY this draft in the GitHub Releases UI (keep the tag), then rerun Recovery."
            fi
            # Verify deletion before creating a new Release.
            after_delete="$(gh release list --repo "$GITHUB_REPOSITORY" --json tagName,isDraft --limit 5000)" || fail 'Cannot recheck deleted draft'
            [[ "$(printf '%s' "$after_delete" | jq --arg tag "$RELEASE_TAG" '[.[] | select(.tagName == $tag)] | length')" == 0 ]] || fail 'Draft still exists after deletion'
            match_count=0
            ;;
        *) fail 'Unrecognized draft state' ;;
    esac
fi

if [[ "$match_count" == 0 ]]; then
    if [[ -n "$existing_commit" ]]; then
        # --verify-tag prevents gh from silently creating/retargeting the tag.
        create_tag_args=(--verify-tag)
    else
        create_tag_args=()
    fi
    create_args=("$RELEASE_TAG" "$MOD_FILE" "$MANIFEST" --repo "$GITHUB_REPOSITORY" --target "$RELEASE_COMMIT" --title "Stay Sharp Medkit Reminder $RELEASE_TAG" --generate-notes "${create_tag_args[@]}")
    [[ "$RECOVERY" != 1 ]] || create_args+=(--latest=false)
    # gh release create natively stages, uploads, then publishes. If it fails
    # midway, it may leave a draft; recovery handles it in a separate run.
    gh release create "${create_args[@]}" || fail 'gh release create failed; check for an interrupted draft'
fi

[[ "$(remote_tag_commit)" == "$RELEASE_COMMIT" ]] || fail 'Tag does not point to the expected commit after publication'
release_json="$(gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --json tagName,isDraft,isPrerelease,assets,url)" || fail 'Published release cannot be inspected'
if ! printf '%s' "$release_json" | jq -e --arg tag "$RELEASE_TAG" --arg mod "$MOD_NAME" '
    .tagName == $tag and .isDraft == false and .isPrerelease == false and
    ([.assets[].name] | sort) == ([$mod, "SHA256SUMS.txt"] | sort)
' >/dev/null; then
    fail 'Published Release is incomplete or contains unexpected assets'
fi

temp_dir="$(mktemp -d)"
trap 'rm -rf -- "$temp_dir"' EXIT
# Verify REAL downloaded bytes, not just names, claimed sizes or remote digest.
gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir "$temp_dir" --pattern "$MOD_NAME" --pattern SHA256SUMS.txt || fail 'Could not download release attachments for verification'
cmp -- "$temp_dir/$MOD_NAME" "$MOD_FILE" || fail 'Published mod differs from the reviewed build'
cmp -- "$temp_dir/SHA256SUMS.txt" "$MANIFEST" || fail 'Published manifest differs from reviewed build'
(cd "$temp_dir" && sha256sum --check --status SHA256SUMS.txt) || fail 'Published asset SHA-256 verification failed'
printf 'Published and verified: https://github.com/%s/releases/tag/%s\n' "$GITHUB_REPOSITORY" "$RELEASE_TAG"
