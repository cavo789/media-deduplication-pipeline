# .devcontainer/scripts/helpers/quality.sh
#
# Category "Quality" — the lint/type/test gate and the formatter.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat Quality
# @cmd check
# @desc Full gate: every pre-commit hook (ruff, mypy, pylint, shellcheck, shfmt, hadolint) then all tests with coverage
function check() {
    (
        cd "$(_repo_root)" || return 1
        printf "🔍 Running pre-commit hooks...\n"
        # Tracked AND untracked (non-ignored) files: `--all-files` would only see what git
        # already tracks, silently skipping every new file.
        git ls-files --cached --others --exclude-standard -z |
            xargs -0 pre-commit run --config .config/.pre-commit-config.yaml --files ||
            return 1
        printf "🧪 Running the test suite with coverage...\n"
        pytest --cov --cov-report=term-missing:skip-covered
    )
}

# @cat Quality
# @cmd format
# @desc Auto-fix: ruff format + ruff check --fix on the whole project
function format() {
    (
        cd "$(_repo_root)" || return 1
        ruff format . && ruff check --fix .
    )
}

# @cat Quality
# @cmd tests
# @desc Run pytest without coverage — pass targets/flags, e.g. 'tests tests/unit/plan -k keeper'
function tests() {
    (
        cd "$(_repo_root)" || return 1
        pytest "$@"
    )
}
