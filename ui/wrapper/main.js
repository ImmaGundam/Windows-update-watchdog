(function () {
  "use strict";

  function getApi() {
    if (!window.pywebview || !window.pywebview.api) {
      throw new Error("pywebview api unavailable");
    }
    return window.pywebview.api;
  }

  function setLight(el, value) {
    el.style.background = value === null ? "gray" : (value ? "green" : "red");
  }

  function watchText(status) {
    const guard = status && status.details && status.details.updates
      ? status.details.updates.guard_enabled
      : false;
    return guard ? "Watching: enabled" : "Watching: disabled";
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
    const svc = document.getElementById("svc");
    const def = document.getElementById("def");
    const main = document.getElementById("main");
    const aboutPage = document.getElementById("aboutPage");
    const msg = document.getElementById("msg");
    const versionText = document.getElementById("versionText");
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const restoreBtn = document.getElementById("restoreBtn");
    const settingsBtn = document.getElementById("settingsBtn");
    const aboutBtn = document.getElementById("aboutBtn");
    const aboutBackBtn = document.getElementById("aboutBackBtn");

    function applyStatus(status) {
      setLight(svc, status ? status.services : null);
      setLight(def, status ? status.defender : null);
      msg.textContent = watchText(status);
      const version = status && status.details ? status.details.version : null;
      if (version && versionText) {
        versionText.textContent = `Version ${version}`;
      }
    }

    async function safeCall(label, fn) {
      try {
        msg.textContent = label;
        const status = await fn();
        applyStatus(status);
      } catch (err) {
        console.error(err);
        setLight(svc, null);
        setLight(def, null);
        msg.textContent = "Error";
      }
    }

    async function refresh() {
      try {
        const status = await getApi().get_status();
        applyStatus(status);
      } catch (err) {
        console.error(err);
        setLight(svc, null);
        setLight(def, null);
      }
    }

    async function openStatusWindow() {
      try {
        msg.textContent = "Opening status...";
        const result = await getApi().open_settings_window();
        msg.textContent = result && result.ok ? "Ready" : "Status error";
      } catch (err) {
        console.error(err);
        msg.textContent = "Status error";
      }
    }

    function showAbout() {
      main.style.display = "none";
      aboutPage.style.display = "block";
    }

    function showMain() {
      aboutPage.style.display = "none";
      main.style.display = "block";
    }

    startBtn.addEventListener("click", function () {
      safeCall("Starting...", function () {
        return getApi().run_all();
      });
    });

    stopBtn.addEventListener("click", function () {
      safeCall("Stopping...", function () {
        return getApi().stop_watchdog();
      });
    });

    restoreBtn.addEventListener("click", function () {
      safeCall("Restoring...", function () {
        return getApi().restore_all();
      });
    });

    settingsBtn.addEventListener("click", openStatusWindow);
    aboutBtn.addEventListener("click", showAbout);
    aboutBackBtn.addEventListener("click", showMain);

    try {
      await waitForApi(40, 100);
      await refresh();
      window.setInterval(refresh, 5000);
    } catch (err) {
      console.error(err);
      setLight(svc, null);
      setLight(def, null);
      msg.textContent = "API error";
    }
  });
})();
