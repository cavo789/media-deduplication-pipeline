# .devcontainer/scripts/helpers/reports.sh
#
# Category "Reports" — serve the HTML reports over HTTP so VS Code can open them in a browser.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat Reports
# @cmd reports
# @desc Serve the HTML reports (default /tmp/media-dedup/reports) on a free port chosen by the OS — 'reports [dir]'
function reports() {
    local -r dir="${1:-/tmp/media-dedup/reports}"
    local -r max_wait_steps=50
    local logfile pid port="" step

    if [[ ! -d "${dir}" ]]; then
        printf "❌ No such directory: %s — run 'demo' first to produce a report.\n" "${dir}" >&2
        return 1
    fi

    # Port 0 lets the kernel pick a free port: nothing hardcoded, several servers can coexist.
    logfile="$(mktemp /tmp/media-dedup-reports.XXXXXX.log)"
    python -m http.server 0 --bind 127.0.0.1 --directory "${dir}" >"${logfile}" 2>&1 &
    pid=$!

    # http.server announces the port it actually bound: "Serving HTTP on ... port 43125 ...".
    for ((step = 0; step < max_wait_steps; step++)); do
        port="$(sed -nE 's/.* port ([0-9]+) .*/\1/p' "${logfile}" | head -1)"
        [[ -n "${port}" ]] && break
        sleep 0.1
    done

    if [[ -z "${port}" ]] || ! kill -0 "${pid}" 2>/dev/null; then
        printf "❌ The report server did not start (PID %s). Logs: %s\n" "${pid}" "${logfile}" >&2
        return 1
    fi

    printf "🚀 Report server started (PID %s) — logs: %s\n\n" "${pid}" "${logfile}"
    printf "  Open in the browser (VS Code forwards the port automatically):\n\n"
    printf "    👉  http://127.0.0.1:%s/index.html\n\n" "${port}"
    printf "  To stop every report server:\n\n    reports_stop\n\n"
}

# @cat Reports
# @cmd reports_stop
# @desc Stop every report server started by 'reports'
function reports_stop() {
    if pkill -f "http.server 0 --bind 127.0.0.1" 2>/dev/null; then
        printf "🛑 Report server(s) stopped.\n"
        return 0
    fi
    printf "ℹ️  No report server was running.\n"
}
