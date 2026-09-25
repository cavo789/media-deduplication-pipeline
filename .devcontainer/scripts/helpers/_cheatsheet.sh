# .devcontainer/scripts/helpers/_cheatsheet.sh
#
# The cheatsheet engine — `welcome()` and the double awk that turns the @cat/@cmd/@desc
# annotations of every sibling module into the startup screen.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# welcome — redraw this cheatsheet. Deliberately un-annotated (no @cat/@cmd), so it doesn't get
# its own one-line section; it's pointed at from the Tip line instead.
function welcome() {
    [[ -t 1 ]] && stty sane 2>/dev/null
    printf "\033[H\033[2J"

    # The annotations live in the sibling modules, not in this file. The fallback keeps `welcome`
    # working if this module is ever sourced on its own.
    local scripts_dir
    scripts_dir="${INTERACTIVE_SCRIPTS_DIR:-$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/..}"

    # PYTHON_VERSION is set by the official python base image: no interpreter spawn needed, so
    # this stays cheap enough to print on every shell startup.
    local uv_version=""
    command -v uv >/dev/null 2>&1 && uv_version="$(uv --version | awk '{print $2}')"

    echo -e "\033[1;34m🧹  Media Dedup — Dev Container\033[0m  \033[2m·  Python ${PYTHON_VERSION:-?}  ·  uv ${uv_version:-?}\033[0m"
    echo -e "   Find and safely clean duplicate photos & videos across folders and disks\n"

    awk '
        /^[ \t]*# @cat[ \t]+/ { sub(/^[ \t]*# @cat[ \t]+/, ""); cat = $0; next; }
        /^[ \t]*# @cmd[ \t]+/ { sub(/^[ \t]*# @cmd[ \t]+/, ""); cmd = $0; next; }
        /^[ \t]*# @desc[ \t]+/ {
            sub(/^[ \t]*# @desc[ \t]+/, ""); desc = $0;
            if (cat != "" && cmd != "") { printf "%s|%s|%s\n", cat, cmd, desc; }
        }
    ' "${scripts_dir}"/helpers/*.sh | sort -t'|' -k1,1 -k2,2 | awk -F'|' '
        {
            if ($1 != current_cat) {
                printf "\r\n\033[1;33m── %s ────────────────────────────────\033[0m\r\n", $1;
                current_cat = $1;
            }
            printf "  \033[1;32m%-16s\033[0m %s\r\n", $2, $3;
        }
    '

    echo -e "\n💡 \033[1;36mTip:\033[0m \033[4mcheck\033[0m before every commit, \033[4mdemo\033[0m then \033[4mreports\033[0m to see the tool at work.  \033[4mwelcome\033[0m redraws this list.\n"
}
