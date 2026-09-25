# .devcontainer/scripts/helpers/todos.sh
#
# Category "Backlog" — a quick look at the open .todos/ backlog (see /todo and /todo-plan).
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat Backlog
# @cmd todos
# @desc List the open TODOs (ID, priority, title) — the execution order lives in .todos/plan.md
function todos() {
    (
        cd "$(_repo_root)" || return 1
        .claude/scripts/todo_parse_backlog.sh .todos | awk -F': ' '
            /^ID: /       { id = $2 }
            /^TITLE: /    { title = substr($0, 8) }
            /^PRIORITY: / { printf "  \033[1;32m%-6s\033[0m \033[2m%-8s\033[0m %s\n", id, $2, title }
        '
    )
}
