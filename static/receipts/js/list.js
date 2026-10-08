(function () {
    "use strict";

    const rows = Array.from(document.querySelectorAll("tr[data-receipt-id]"));
    if (rows.length === 0) return;

    const POLL_INTERVAL_MS = 15000;
    const INITIAL_DELAY_MS = 3000;

    const idsQuery = rows.map((r) => r.dataset.receiptId).join(",");
    const baseUrl = `/api/receipts/?ids=${encodeURIComponent(idsQuery)}`;

    let pollTimer = null;

    function log(...args) {
        if (DEBUG) console.log("[polling]", ...args);
    }

    function readCurrentStatus(row) {
        if (row.dataset.status) return row.dataset.status;
        const badge = row.querySelector(".badge");
        if (badge) {
            const m = badge.className.match(/badge--([a-z]+)/);
            if (m) return m[1];
        }
        return null;
    }

    function findBadge(row) {
        return (
            row.querySelector('[data-cell="status"] .badge') ||
            row.querySelector('td[data-label="Статус"] .badge') ||
            row.querySelector(".badge")
        );
    }

    function findReasonCell(row) {
        return (
            row.querySelector('[data-cell="reason"]') ||
            row.querySelector('td[data-label="Причина отказа"]')
        );
    }

    function flashRow(row) {
        row.classList.remove("row--updated");
        void row.offsetWidth;
        row.classList.add("row--updated");
        window.setTimeout(() => row.classList.remove("row--updated"), 2600);
    }

    function updateRow(row, fresh) {
        const badge = findBadge(row);
        log(`row #${row.dataset.receiptId}: badge element =`, badge);

        if (badge) {
            badge.textContent = fresh.status_display;
            badge.className = "badge badge--" + fresh.status;
        }

        const reasonCell = findReasonCell(row);
        if (reasonCell) {
            reasonCell.textContent = fresh.rejection_reason || "—";
        }

        row.dataset.status = fresh.status;
        flashRow(row);
    }

    async function pollStatuses() {
        const url = baseUrl + "&_=" + Date.now();

        try {
            const resp = await fetch(url, {
                headers: { "Accept": "application/json" },
                credentials: "same-origin",
                cache: "no-store",
            });
            if (!resp.ok) {
                log("http error", resp.status);
                return;
            }

            const data = await resp.json();
            if (!data || !Array.isArray(data.results)) {
                log("bad payload", data);
                return;
            }

            log(`fetched ${data.results.length} receipts`);

            const byId = Object.fromEntries(
                data.results.map((r) => [String(r.id), r])
            );

            for (const row of rows) {
                const id = String(row.dataset.receiptId);
                const current = readCurrentStatus(row);
                const fresh = byId[id];
                if (!fresh) continue;

                log(`row #${id}: "${current}" → "${fresh.status}"`);

                if (fresh.status !== current) {
                    updateRow(row, fresh);
                }
            }
        } catch (err) {
            log("fetch failed", err);
        }
    }

    function startPolling() {
        if (pollTimer !== null) return;
        pollTimer = window.setInterval(pollStatuses, POLL_INTERVAL_MS);
    }

    function stopPolling() {
        if (pollTimer === null) return;
        window.clearInterval(pollTimer);
        pollTimer = null;
    }

    window.setTimeout(pollStatuses, INITIAL_DELAY_MS);
    startPolling();

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopPolling();
        } else {
            pollStatuses();
            startPolling();
        }
    });
})();
