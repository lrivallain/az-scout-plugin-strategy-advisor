// Strategy Advisor plugin tab logic
// This script runs after app.js and can use its globals:
//   - apiFetch(url)    – GET helper with error handling
//   - apiPost(url, body) – POST helper
//   - tenantQS(prefix) – returns "?tenantId=…" or ""
//   - subscriptions    – array of {id, name} for the current tenant
//   - regions          – array of {name, displayName}
//   - escapeHtml(str)  – HTML-escape utility
//   - showError(id, msg) / hideError(id)
//   - formatNum(n, decimals)
// Static assets are served at /plugins/strategy/static/
(function () {
    const PLUGIN_NAME = "strategy";
    const API_BASE = "/plugins/" + PLUGIN_NAME;
    const container = document.getElementById("plugin-tab-" + PLUGIN_NAME);
    if (!container) return;

    let _stratSubscriptionId = null;

    // -----------------------------------------------------------------------
    // 1. Load HTML fragment
    // -----------------------------------------------------------------------
    fetch(`${API_BASE}/static/html/strategy-tab.html`)
        .then(resp => resp.text())
        .then(html => {
            container.innerHTML = html;
            initStrategyPlugin();
        })
        .catch(err => {
            container.innerHTML = `<div class="alert alert-danger">Failed to load Strategy Advisor UI: ${err.message}</div>`;
        });

    // -----------------------------------------------------------------------
    // 2. Plugin initialisation (called after HTML is injected)
    // -----------------------------------------------------------------------
    function initStrategyPlugin() {
        initStratSubCombobox();
    }

    // -----------------------------------------------------------------------
    // Subscription combobox
    // -----------------------------------------------------------------------
    function initStratSubCombobox() {
        const searchInput = document.getElementById("strat-sub-search");
        const dropdown = document.getElementById("strat-sub-dropdown");
        if (!searchInput || !dropdown) return;

        searchInput.addEventListener("focus", () => {
            searchInput.select();
            renderStratSubDropdown(searchInput.value.includes("(") ? "" : searchInput.value);
            dropdown.classList.add("show");
        });
        searchInput.addEventListener("input", () => {
            document.getElementById("strat-sub-select").value = "";
            _stratSubscriptionId = null;
            renderStratSubDropdown(searchInput.value);
            dropdown.classList.add("show");
        });
        searchInput.addEventListener("keydown", (e) => {
            const items = dropdown.querySelectorAll("li");
            const active = dropdown.querySelector("li.active");
            let idx = [...items].indexOf(active);
            if (e.key === "ArrowDown") {
                e.preventDefault();
                if (!dropdown.classList.contains("show")) dropdown.classList.add("show");
                if (active) active.classList.remove("active");
                idx = (idx + 1) % items.length;
                items[idx]?.classList.add("active");
                items[idx]?.scrollIntoView({ block: "nearest" });
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                if (active) active.classList.remove("active");
                idx = idx <= 0 ? items.length - 1 : idx - 1;
                items[idx]?.classList.add("active");
                items[idx]?.scrollIntoView({ block: "nearest" });
            } else if (e.key === "Enter") {
                e.preventDefault();
                if (active) selectStratSub(active.dataset.value);
                else if (items.length === 1) selectStratSub(items[0].dataset.value);
            } else if (e.key === "Escape") {
                dropdown.classList.remove("show");
                searchInput.blur();
            }
        });
        document.addEventListener("click", (e) => {
            if (!e.target.closest("#strat-sub-combobox")) dropdown.classList.remove("show");
        });

        // Re-render when subscriptions change (tenant switch)
        const tenantEl = document.getElementById("tenant-select");
        if (tenantEl) {
            tenantEl.addEventListener("change", () => {
                _stratSubscriptionId = null;
                const si = document.getElementById("strat-sub-search");
                if (si) { si.value = ""; }
                document.getElementById("strat-sub-select").value = "";
            });
        }
    }

    function renderStratSubDropdown(filter) {
        const dropdown = document.getElementById("strat-sub-dropdown");
        if (!dropdown) return;
        const lc = (filter || "").toLowerCase();
        const matches = lc
            ? subscriptions.filter(s => s.name.toLowerCase().includes(lc) || s.id.toLowerCase().includes(lc))
            : subscriptions;
        dropdown.innerHTML = matches.map(s =>
            `<li class="dropdown-item" data-value="${s.id}">${escapeHtml(s.name)} <span class="region-name">(${s.id.slice(0, 8)}\u2026)</span></li>`
        ).join("");
        dropdown.querySelectorAll("li").forEach(li => {
            li.addEventListener("click", () => selectStratSub(li.dataset.value));
        });
        const searchInput = document.getElementById("strat-sub-search");
        if (subscriptions.length > 0 && searchInput) {
            searchInput.placeholder = "Type to search subscriptions\u2026";
            searchInput.disabled = false;
        }
    }

    function selectStratSub(id) {
        const s = subscriptions.find(s => s.id === id);
        if (!s) return;
        _stratSubscriptionId = id;
        document.getElementById("strat-sub-select").value = id;
        document.getElementById("strat-sub-search").value = s.name;
        document.getElementById("strat-sub-dropdown").classList.remove("show");
    }

    // -----------------------------------------------------------------------
    // Form submission
    // -----------------------------------------------------------------------
    // Expose submitStrategy globally so the form onsubmit can call it
    window.submitStrategy = async function (e) {
        e.preventDefault();

        const subId = _stratSubscriptionId;
        if (!subId) { showError("strategy-error", "Please select a subscription."); return; }

        hideError("strategy-error");
        document.getElementById("strategy-results").classList.add("d-none");
        document.getElementById("strategy-loading").classList.remove("d-none");
        document.getElementById("strat-submit-btn").disabled = true;

        const body = {
            workloadName: document.getElementById("strat-workload-name").value.trim(),
            subscriptionId: subId,
            tenantId: document.getElementById("tenant-select")?.value || undefined,
            scale: {
                sku: document.getElementById("strat-sku").value.trim() || undefined,
                instanceCount: parseInt(document.getElementById("strat-instances").value, 10) || 1,
                gpuCountTotal: parseInt(document.getElementById("strat-gpu").value, 10) || undefined,
            },
            constraints: {
                dataResidency: document.getElementById("strat-residency").value || undefined,
                requireZonal: document.getElementById("strat-require-zonal").checked,
                maxInterRegionRttMs: parseInt(document.getElementById("strat-max-rtt").value, 10) || undefined,
            },
            usage: {
                statefulness: document.getElementById("strat-statefulness").value,
                crossRegionTraffic: document.getElementById("strat-cross-traffic").value,
                latencySensitivity: document.getElementById("strat-latency-sens").value,
            },
            data: {},
            timing: {
                deploymentUrgency: document.getElementById("strat-urgency").value,
            },
            pricing: {
                currencyCode: document.getElementById("strat-currency").value,
                preferSpot: document.getElementById("strat-prefer-spot").checked,
                maxHourlyBudget: parseFloat(document.getElementById("strat-budget").value) || undefined,
            },
        };

        try {
            const result = await apiPost(API_BASE + "/capacity-strategy", body);
            renderStrategyResults(result);
        } catch (err) {
            showError("strategy-error", "Strategy computation failed: " + err.message);
        } finally {
            document.getElementById("strategy-loading").classList.add("d-none");
            document.getElementById("strat-submit-btn").disabled = false;
        }
    };

    // -----------------------------------------------------------------------
    // Results rendering
    // -----------------------------------------------------------------------
    function renderStrategyResults(data) {
        const resultsEl = document.getElementById("strategy-results");
        resultsEl.classList.remove("d-none");

        // Summary cards
        const summary = data.summary || {};
        const cards = document.getElementById("strategy-summary-cards");
        const confLbl = (summary.overallConfidenceLabel || "unknown").toLowerCase().replace(/\s+/g, "-");
        const stratLabel = (summary.strategy || "").replace(/_/g, " ");
        const costStr = summary.estimatedHourlyCost != null
            ? `${formatNum(summary.estimatedHourlyCost, 2)} ${escapeHtml(summary.currency || "USD")}/h`
            : "\u2014";
        cards.innerHTML = `
            <div class="col-md-3"><div class="card text-center p-3">
                <div class="text-body-secondary small">Strategy</div>
                <div class="fw-bold text-capitalize">${escapeHtml(stratLabel)}</div>
            </div></div>
            <div class="col-md-3"><div class="card text-center p-3">
                <div class="text-body-secondary small">Regions</div>
                <div class="fw-bold">${summary.regionCount ?? "\u2014"}</div>
            </div></div>
            <div class="col-md-3"><div class="card text-center p-3">
                <div class="text-body-secondary small">Instances</div>
                <div class="fw-bold">${summary.totalInstances ?? "\u2014"}</div>
            </div></div>
            <div class="col-md-3"><div class="card text-center p-3">
                <div class="text-body-secondary small">Confidence</div>
                <div><span class="confidence-badge confidence-${confLbl}">${summary.overallConfidence ?? "\u2014"} ${escapeHtml(summary.overallConfidenceLabel || "")}</span></div>
            </div></div>
        `;

        // Business view
        const biz = data.businessView || {};
        const bizEl = document.getElementById("strategy-business");
        let bizHtml = `<p class="fw-bold">${escapeHtml(biz.keyMessage || "")}</p>`;
        if (biz.justification?.length) {
            bizHtml += "<h6>Justification</h6><ul>" + biz.justification.map(j => `<li>${escapeHtml(j)}</li>`).join("") + "</ul>";
        }
        if (biz.risks?.length) {
            bizHtml += '<h6>Risks</h6><ul class="text-warning">' + biz.risks.map(r => `<li>${escapeHtml(r)}</li>`).join("") + "</ul>";
        }
        if (biz.mitigations?.length) {
            bizHtml += '<h6>Mitigations</h6><ul class="text-success">' + biz.mitigations.map(m => `<li>${escapeHtml(m)}</li>`).join("") + "</ul>";
        }
        bizHtml += `<p class="text-body-secondary small mt-2">Estimated cost: ${costStr}</p>`;
        bizEl.innerHTML = bizHtml;

        // Technical view
        const tech = data.technicalView || {};
        const techEl = document.getElementById("strategy-technical");
        let techHtml = "";

        // Allocations table
        if (tech.allocations?.length) {
            techHtml += '<h6>Region Allocations</h6><div class="table-responsive"><table class="table table-sm table-hover"><thead><tr>';
            techHtml += "<th>Region</th><th>Role</th><th>SKU</th><th>Instances</th><th>Zones</th><th>Quota Rem.</th><th>Spot</th><th>Confidence</th><th>RTT (ms)</th><th>PAYGO/h</th><th>Spot/h</th>";
            techHtml += "</tr></thead><tbody>";
            tech.allocations.forEach(a => {
                const aConfLbl = (a.confidenceLabel || "").toLowerCase().replace(/\s+/g, "-");
                techHtml += "<tr>";
                techHtml += `<td>${escapeHtml(a.region)}</td>`;
                techHtml += `<td><span class="badge bg-secondary">${escapeHtml(a.role)}</span></td>`;
                techHtml += `<td>${escapeHtml(a.sku)}</td>`;
                techHtml += `<td>${a.instanceCount}</td>`;
                techHtml += `<td>${a.zones?.length ? a.zones.join(", ") : "\u2014"}</td>`;
                techHtml += `<td>${a.quotaRemaining ?? "\u2014"}</td>`;
                techHtml += `<td>${a.spotScore ? `<span class="spot-badge spot-${a.spotScore.toLowerCase()}">${escapeHtml(a.spotScore)}</span>` : "\u2014"}</td>`;
                techHtml += `<td>${a.confidenceScore != null ? `<span class="confidence-badge confidence-${aConfLbl}">${a.confidenceScore}</span>` : "\u2014"}</td>`;
                techHtml += `<td>${a.rttFromPrimaryMs ?? "\u2014"}</td>`;
                techHtml += `<td class="price-cell">${a.paygoPerHour != null ? formatNum(a.paygoPerHour, 4) : "\u2014"}</td>`;
                techHtml += `<td class="price-cell">${a.spotPerHour != null ? formatNum(a.spotPerHour, 4) : "\u2014"}</td>`;
                techHtml += "</tr>";
            });
            techHtml += "</tbody></table></div>";
        }

        // Latency matrix
        if (tech.latencyMatrix && Object.keys(tech.latencyMatrix).length > 1) {
            const rgs = Object.keys(tech.latencyMatrix).sort();
            techHtml += '<h6 class="mt-3">Inter-region Latency (ms)</h6><div class="table-responsive"><table class="table table-sm table-bordered"><thead><tr><th></th>';
            rgs.forEach(r => { techHtml += `<th>${escapeHtml(r)}</th>`; });
            techHtml += "</tr></thead><tbody>";
            rgs.forEach(src => {
                techHtml += `<tr><td class="fw-bold">${escapeHtml(src)}</td>`;
                rgs.forEach(dst => {
                    const v = tech.latencyMatrix[src]?.[dst];
                    techHtml += `<td class="text-center">${v != null ? v : "\u2014"}</td>`;
                });
                techHtml += "</tr>";
            });
            techHtml += "</tbody></table></div>";
        }

        if (tech.evaluatedAt) {
            techHtml += `<p class="text-body-secondary small">Evaluated at: ${escapeHtml(tech.evaluatedAt)}</p>`;
        }
        techEl.innerHTML = techHtml || '<p class="text-body-secondary">No technical details available.</p>';

        // Warnings
        const warnEl = document.getElementById("strategy-warnings");
        const allWarnings = [...(data.warnings || []), ...(data.missingInputs || [])];
        if (allWarnings.length) {
            warnEl.innerHTML = allWarnings.map(w =>
                `<div class="alert alert-warning alert-sm py-1 px-2 mb-1"><i class="bi bi-exclamation-triangle"></i> ${escapeHtml(w)}</div>`
            ).join("");
        } else {
            warnEl.innerHTML = "";
        }

        // Errors
        if (data.errors?.length) {
            showError("strategy-error", data.errors.join("; "));
        }
    }
})();
