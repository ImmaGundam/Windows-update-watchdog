(function () {
  "use strict";

  const DEFAULT_INTERVAL_SECONDS = 600;
  const MAX_INTERVAL_SECONDS = 43200;

  function getApi() {
    if (!window.pywebview || !window.pywebview.api) {
      throw new Error("pywebview api unavailable");
    }
    return window.pywebview.api;
  }

  function lightColor(value) {
    if (value === null || value === undefined) {
      return "gray";
    }
    return value ? "green" : "red";
  }

  function setLight(el, value) {
    el.style.background = lightColor(value);
  }

  function parseValue(el) {
    const value = parseInt(el.value || "0", 10);
    if (!Number.isFinite(value)) {
      return 1;
    }
    return Math.min(MAX_INTERVAL_SECONDS, Math.max(1, value));
  }

  function buildRow(name, status, meta, ignored) {
    const div = document.createElement("div");
    div.className = "row";

    const light = document.createElement("span");
    light.className = "light";
    light.style.background = ignored ? "gray" : lightColor(status);

    const label = document.createElement("span");
    label.className = "name";
    label.textContent = name;

    const detail = document.createElement("span");
    detail.className = "meta";
    detail.textContent = meta || "";

    div.appendChild(light);
    div.appendChild(label);
    div.appendChild(detail);
    return div;
  }

  function updateServiceOk(svc) {
    if (!svc || !svc.exists) {
      return null;
    }
    return svc.state !== "Running" && svc.start_type === "Disabled";
  }

  function optionalUpdateServiceOk(svc) {
    if (!svc || !svc.exists) {
      return null;
    }
    if (svc.state === "Running") {
      return false;
    }
    return null;
  }

  function defenderServiceOk(svc, role) {
    if (!svc || !svc.exists) {
      return role === "optional" ? null : false;
    }
    if (role === "core") {
      return svc.state === "Running" && svc.start_type !== "Disabled";
    }
    return svc.start_type !== "Disabled";
  }

  function boolMeta(value) {
    if (value === true) {
      return "True";
    }
    if (value === false) {
      return "False";
    }
    return "Unknown";
  }

  function pluralize(value, unit) {
    return `${value} ${unit}${value === 1 ? "" : "s"}`;
  }

  function formatDuration(seconds) {
    let remaining = Math.min(MAX_INTERVAL_SECONDS, Math.max(1, parseInt(seconds || "1", 10)));
    const days = Math.floor(remaining / 86400);
    remaining %= 86400;
    const hours = Math.floor(remaining / 3600);
    remaining %= 3600;
    const minutes = Math.floor(remaining / 60);
    remaining %= 60;

    const parts = [];
    if (days) {
      parts.push(pluralize(days, "day"));
    }
    if (hours) {
      parts.push(pluralize(hours, "hour"));
    }
    if (minutes) {
      parts.push(pluralize(minutes, "minute"));
    }
    if (remaining || parts.length === 0) {
      parts.push(pluralize(remaining, "second"));
    }

    return parts.join(" ");
  }

  async function waitForApi(maxAttempts, delayMs) {
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      if (window.pywebview && window.pywebview.api) {
        return window.pywebview.api;
      }
      await new Promise(resolve => window.setTimeout(resolve, delayMs));
    }
    throw new Error("pywebview api unavailable");
  }

  document.addEventListener("DOMContentLoaded", async function () {
    const summaryUpdates = document.getElementById("summaryUpdates");
    const summaryDefender = document.getElementById("summaryDefender");
    const summaryUpdatesText = document.getElementById("summaryUpdatesText");
    const summaryDefenderText = document.getElementById("summaryDefenderText");
    const updateRows = document.getElementById("updateRows");
    const defenderRows = document.getElementById("defenderRows");
    const mpRows = document.getElementById("mpRows");
    const terminal = document.getElementById("terminal");
    const defenderBox = document.getElementById("defenderBox");
    const ignoreDefender = document.getElementById("ignoreDefender");
    const intervalValue = document.getElementById("intervalValue") || document.getElementById("intervalSeconds");
    const intervalUnit = document.getElementById("intervalUnit");
    const applyIntervalBtn = document.getElementById("applyIntervalBtn");
    const fixDefenderBtn = document.getElementById("fixDefenderBtn");
    const timerMeta = document.getElementById("timerMeta");
    const message = document.getElementById("message");
    let lastLogText = null;
    let maxIntervalSeconds = MAX_INTERVAL_SECONDS;

    function captureViewport() {
      return {
        x: window.scrollX || window.pageXOffset || 0,
        y: window.scrollY || window.pageYOffset || 0,
        terminalTop: terminal.scrollTop
      };
    }

    function restoreViewport(viewport) {
      terminal.scrollTop = Math.min(viewport.terminalTop, terminal.scrollHeight);
      window.scrollTo(viewport.x, viewport.y);
    }

    function appendTerminalLine(text) {
      const viewport = captureViewport();
      terminal.textContent += text;
      restoreViewport(viewport);
    }

    function setTimerMeta(seconds) {
      const total = Math.min(maxIntervalSeconds, Math.max(1, parseInt(seconds || "1", 10)));
      timerMeta.textContent = formatDuration(total);
      timerMeta.title = `${pluralize(total, "second")} between checks`;
    }

    function renderStatus(status) {
      setLight(summaryUpdates, status.services);
      setLight(summaryDefender, status.defender);
      summaryUpdatesText.textContent = status.services ? "OK" : "Check";
      summaryDefenderText.textContent = status.defender === null ? "Ignored" : (status.defender ? "OK" : "Check");

      const details = status.details || {};
      maxIntervalSeconds = details.guard_interval_max_seconds || MAX_INTERVAL_SECONDS;
      const ignored = details.ignore_defender === true;
      if (document.activeElement !== ignoreDefender) {
        ignoreDefender.checked = ignored;
      }
      if (intervalValue && document.activeElement !== intervalValue) {
        intervalValue.max = String(maxIntervalSeconds);
        intervalValue.value = details.guard_interval_seconds || DEFAULT_INTERVAL_SECONDS;
      }

      setTimerMeta(
        intervalValue && document.activeElement === intervalValue
          ? parseValue(intervalValue)
          : details.guard_interval_seconds || DEFAULT_INTERVAL_SECONDS
      );
      message.textContent = details.updates && details.updates.guard_enabled ? "Status: enabled" : "Status: disabled";

      defenderBox.classList.toggle("ignored-card", ignored);

      const updates = details.updates || {};
      const defender = details.defender || {};

      updateRows.innerHTML = "";
      (updates.services || []).forEach(function (svc) {
        updateRows.appendChild(buildRow(
          svc.name,
          updateServiceOk(svc),
          `${svc.state} / ${svc.start_type}`,
          false
        ));
      });

      (updates.optional_services || []).forEach(function (svc) {
        updateRows.appendChild(buildRow(
          `${svc.name} optional`,
          optionalUpdateServiceOk(svc),
          `${svc.state} / ${svc.start_type}`,
          false
        ));
      });

      updateRows.appendChild(buildRow(
        "NoAutoUpdate policy",
        updates.policy_disabled === true,
        updates.policy_disabled ? "Enabled" : "Missing",
        false
      ));
      updateRows.appendChild(buildRow(
        "Update guard",
        updates.guard_enabled === true,
        updates.guard_enabled ? "Enabled" : "Off",
        false
      ));

      defenderRows.innerHTML = "";
      if (defender.core) {
        defenderRows.appendChild(buildRow(
          defender.core.name,
          defenderServiceOk(defender.core, "core"),
          `${defender.core.state} / ${defender.core.start_type}`,
          ignored
        ));
      }

      (defender.support || []).forEach(function (svc) {
        defenderRows.appendChild(buildRow(
          svc.name,
          defenderServiceOk(svc, "support"),
          `${svc.state} / ${svc.start_type}`,
          ignored
        ));
      });

      (defender.optional || []).forEach(function (svc) {
        defenderRows.appendChild(buildRow(
          `${svc.name} optional`,
          defenderServiceOk(svc, "optional"),
          `${svc.state} / ${svc.start_type}`,
          ignored
        ));
      });

      mpRows.innerHTML = "";
      const mp = defender.mp_status || {};
      const data = mp.data || {};
      mpRows.appendChild(buildRow("Get-MpComputerStatus", mp.ok === true, mp.ok ? "OK" : "Check", ignored));
      mpRows.appendChild(buildRow("AntivirusEnabled", data.AntivirusEnabled === true, boolMeta(data.AntivirusEnabled), ignored));
      mpRows.appendChild(buildRow("RealTimeProtection", data.RealTimeProtectionEnabled === true, boolMeta(data.RealTimeProtectionEnabled), ignored));
      mpRows.appendChild(buildRow("AMServiceEnabled", data.AMServiceEnabled === true, boolMeta(data.AMServiceEnabled), ignored));
      mpRows.appendChild(buildRow("TamperProtected", data.IsTamperProtected === true, boolMeta(data.IsTamperProtected), ignored));
    }

    function renderStatusPreservingViewport(status) {
      const viewport = captureViewport();
      renderStatus(status);
      restoreViewport(viewport);
    }

    async function refresh() {
      try {
        const status = await getApi().get_status();
        renderStatusPreservingViewport(status);
      } catch (err) {
        appendTerminalLine("\n[error] status refresh failed: " + err);
        message.textContent = "Status error";
      }

      try {
        const log = await getApi().get_activity_log();
        const nextLogText = (log.lines || []).join("\n");
        if (nextLogText !== lastLogText) {
          const viewport = captureViewport();
          terminal.textContent = nextLogText;
          lastLogText = nextLogText;
          restoreViewport(viewport);
        }
      } catch (err) {
        appendTerminalLine("\n[error] log refresh failed: " + err);
      }
    }

    async function fixDefender() {
      try {
        fixDefenderBtn.disabled = true;
        fixDefenderBtn.textContent = "Fixing...";
        const status = await getApi().fix_defender();
        renderStatusPreservingViewport(status);
      } catch (err) {
        console.error(err);
        message.textContent = "Defender error";
      } finally {
        fixDefenderBtn.disabled = false;
        fixDefenderBtn.textContent = "Fix Defender";
      }
    }

    async function applyInterval() {
      try {
        applyIntervalBtn.disabled = true;
        if (intervalValue) {
          intervalValue.value = String(parseValue(intervalValue));
        }
        const status = await getApi().set_guard_interval(
          parseValue(intervalValue),
          intervalUnit ? intervalUnit.value : "seconds"
        );
        renderStatusPreservingViewport(status);
      } catch (err) {
        console.error(err);
        message.textContent = "Interval update failed";
      } finally {
        applyIntervalBtn.disabled = false;
      }
    }

    ignoreDefender.addEventListener("change", async function () {
      try {
        const status = await getApi().toggle_ignore(ignoreDefender.checked);
        renderStatusPreservingViewport(status);
      } catch (err) {
        console.error(err);
        message.textContent = "Ignore update failed";
      }
    });

    if (intervalValue) {
      intervalValue.addEventListener("input", function () {
        if (parseInt(intervalValue.value || "0", 10) > maxIntervalSeconds) {
          intervalValue.value = String(maxIntervalSeconds);
        }
        setTimerMeta(parseValue(intervalValue));
      });
      intervalValue.addEventListener("change", applyInterval);
    }
    if (intervalUnit) {
      intervalUnit.addEventListener("change", applyInterval);
    }
    applyIntervalBtn.addEventListener("click", applyInterval);
    fixDefenderBtn.addEventListener("click", fixDefender);

    try {
      await waitForApi(40, 100);
      await refresh();
      window.setInterval(refresh, 2000);
    } catch (err) {
      console.error(err);
      message.textContent = "API error";
    }
  });
})();
