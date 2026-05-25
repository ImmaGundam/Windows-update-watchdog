(function () {
  "use strict";

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
    return Number.isFinite(value) && value >= 0 ? value : 0;
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

    function renderStatus(status) {
      setLight(summaryUpdates, status.services);
      setLight(summaryDefender, status.defender);
      summaryUpdatesText.textContent = status.services ? "OK" : "Check";
      summaryDefenderText.textContent = status.defender === null ? "Ignored" : (status.defender ? "OK" : "Check");

      const details = status.details || {};
      const ignored = details.ignore_defender === true;
      if (document.activeElement !== ignoreDefender) {
        ignoreDefender.checked = ignored;
      }
      if (intervalValue && document.activeElement !== intervalValue) {
        intervalValue.value = details.guard_interval_seconds || 600;
      }

      timerMeta.textContent = `${details.guard_interval_seconds || 600} second(s)`;
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

    async function refresh() {
      try {
        const status = await getApi().get_status();
        renderStatus(status);
      } catch (err) {
        terminal.textContent += "\n[error] status refresh failed: " + err;
        message.textContent = "Status error";
      }

      try {
        const log = await getApi().get_activity_log();
        terminal.textContent = (log.lines || []).join("\n");
        terminal.scrollTop = terminal.scrollHeight;
      } catch (err) {
        terminal.textContent += "\n[error] log refresh failed: " + err;
      }
    }

    async function fixDefender() {
      try {
        fixDefenderBtn.disabled = true;
        fixDefenderBtn.textContent = "Fixing...";
        const status = await getApi().fix_defender();
        renderStatus(status);
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
        const status = await getApi().set_guard_interval(
          parseValue(intervalValue),
          intervalUnit ? intervalUnit.value : "seconds"
        );
        renderStatus(status);
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
        renderStatus(status);
      } catch (err) {
        console.error(err);
        message.textContent = "Ignore update failed";
      }
    });

    if (intervalValue) {
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
