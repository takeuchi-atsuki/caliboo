#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# 配布ZIPには開発者向けのSSH設定を含めない。存在する場合だけ追加する。
# Keep any SSH configuration forwarded or supplied by VS Code.
if [[ -f .devcontainer/ssh_config ]]; then
    install -d -m 700 "${HOME}/.ssh"
    touch "${HOME}/.ssh/config"
    chmod 600 "${HOME}/.ssh/config"
    marker='# BEGIN devcontainer GitHub settings'
    if ! grep -Fxq "$marker" "${HOME}/.ssh/config"; then
        temp_config="$(mktemp "${HOME}/.ssh/config.XXXXXXXX")"
        chmod 600 "$temp_config"
        {
            printf '%s\n' "$marker"
            cat .devcontainer/ssh_config
            printf '%s\n' '# END devcontainer GitHub settings'
            cat "${HOME}/.ssh/config"
        } > "$temp_config"
        mv "$temp_config" "${HOME}/.ssh/config"
    fi
fi

# This project hook is invoked only when present in the repository.
if [[ -f ./devel/setup.sh ]]; then
    sudo bash ./devel/setup.sh --system
fi
