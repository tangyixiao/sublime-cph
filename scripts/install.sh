#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data_dir="${XDG_CONFIG_HOME:-$HOME/.config}/sublime-text"
package_dir="$data_dir/Packages/CompetitiveHelper"
user_dir="$data_dir/Packages/User"
backup_dir="$data_dir/Backups/sublime-cph-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$user_dir" "$data_dir/Backups"

for path in \
  "$user_dir/CPH C++.sublime-build" \
  "$user_dir/Default (Linux).sublime-keymap"; do
  if [ -e "$path" ] || [ -L "$path" ]; then
    mkdir -p "$backup_dir"
    cp -a "$path" "$backup_dir/"
  fi
done

if [ -e "$package_dir" ] || [ -L "$package_dir" ]; then
  mkdir -p "$backup_dir"
  mv "$package_dir" "$backup_dir/CompetitiveHelper"
fi

ln -s "$repo_dir/CompetitiveHelper" "$package_dir"
cp "$repo_dir/builds/CPH C++.sublime-build" "$user_dir/CPH C++.sublime-build"
cp "$repo_dir/keymaps/Default (Linux).sublime-keymap" "$user_dir/Default (Linux).sublime-keymap"

printf 'Installed CompetitiveHelper from %s\n' "$repo_dir"
printf 'Backup directory: %s\n' "$backup_dir"
