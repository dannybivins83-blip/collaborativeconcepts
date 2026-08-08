/* ============================================================
   Gatekeeper Fence Co. — site behavior
   Mobile nav + AJAX quote form (FormSubmit).
   Lead destination is set in GK_CONFIG (see each page's <head>).
   ============================================================ */
(function () {
  "use strict";

  /* ---------- mobile nav ---------- */
  var toggle = document.querySelector(".navtoggle");
  var nav = document.getElementById("nav");
  var scrim = document.querySelector(".navscrim");

  if (toggle && nav) {
    if (scrim) scrim.hidden = false;

    function setNav(open) {
      nav.setAttribute("data-open", open ? "true" : "false");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      if (scrim) scrim.setAttribute("data-open", open ? "true" : "false");
      document.body.style.overflow = open ? "hidden" : "";
    }

    toggle.addEventListener("click", function () {
      setNav(nav.getAttribute("data-open") !== "true");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a") || e.target.closest(".navclose")) setNav(false);
    });
    if (scrim) scrim.addEventListener("click", function () { setNav(false); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.getAttribute("data-open") === "true") {
        setNav(false);
        toggle.focus();
      }
    });
    // a resize past the desktop breakpoint should never leave body scroll locked
    window.addEventListener("resize", function () {
      if (window.innerWidth > 1000 && nav.getAttribute("data-open") === "true") setNav(false);
    });
  }

  /* ---------- quote forms ---------- */
  var cfg = window.GK_CONFIG || {};
  var endpoint = cfg.FORM_ENDPOINT;

  Array.prototype.forEach.call(document.querySelectorAll("form[data-gkform]"), function (form) {
    var msg = form.querySelector(".formmsg");
    var btn = form.querySelector("button[type=submit]");

    function say(state, text) {
      if (!msg) return;
      msg.setAttribute("data-state", state);
      msg.textContent = text;
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();

      // honeypot — silently succeed for bots
      var hp = form.querySelector("input[name=_honey]");
      if (hp && hp.value) { say("ok", "Thanks — we'll be in touch."); form.reset(); return; }

      if (!endpoint) {
        say("err", "This form isn't connected yet. Please call 561-503-6502.");
        return;
      }

      var data = new FormData(form);
      data.append("_subject", "New fence estimate request — " + (data.get("name") || "website"));
      data.append("_template", "table");
      data.append("Page", window.location.pathname);

      var original = btn ? btn.textContent : "";
      if (btn) { btn.disabled = true; btn.textContent = "Sending…"; }
      say("", "");

      fetch(endpoint, {
        method: "POST",
        body: data,
        headers: { Accept: "application/json" }
      })
        .then(function (r) { if (!r.ok) throw new Error("bad status " + r.status); return r.json(); })
        .then(function () {
          form.reset();
          say("ok", "Got it — thanks. We'll call you back to set up a free on-site estimate. Need us sooner? Call 561-503-6502.");
        })
        .catch(function () {
          say("err", "Something went wrong sending that. Please call or text 561-503-6502 and we'll take care of you.");
        })
        .finally(function () {
          if (btn) { btn.disabled = false; btn.textContent = original; }
        });
    });
  });

  /* ---------- current-year stamps ---------- */
  Array.prototype.forEach.call(document.querySelectorAll("[data-year]"), function (el) {
    el.textContent = new Date().getFullYear();
  });
})();
