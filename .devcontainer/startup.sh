#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SSH_AUTH_SOCK:-}" || ! -S "${SSH_AUTH_SOCK:-/nonexistent}" ]]; then
    echo 'GitHub SSH: SSH agent is unavailable. Start ssh-agent and add your key on the Docker host, then reopen the container.' >&2
elif ! ssh-add -l >/dev/null 2>&1; then
    echo 'GitHub SSH: no key is loaded in the forwarded SSH agent. Run ssh-add on the Docker host.' >&2
fi
