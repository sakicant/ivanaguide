/* Private Walking Tours by Ivana — small, dependency-free interactions */
(function () {
  "use strict";

  // ---- mobile nav ---------------------------------------------------------
  var toggle = document.querySelector(".nav-toggle");
  var mobileNav = document.getElementById("mobileNav");
  if (toggle && mobileNav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      mobileNav.hidden = false;               // ensure it can display
      mobileNav.classList.toggle("open", !open);
      document.body.style.overflow = !open ? "hidden" : "";
    });
    mobileNav.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        toggle.setAttribute("aria-expanded", "false");
        mobileNav.classList.remove("open");
        document.body.style.overflow = "";
      });
    });
  }

  // ---- header shadow on scroll -------------------------------------------
  var header = document.getElementById("siteHeader");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("scrolled", window.scrollY > 12);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // ---- reveal on scroll ---------------------------------------------------
  var reveals = document.querySelectorAll(".reveal");
  if (reveals.length && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("in"); });
  }

  // ---- contact form: graceful AJAX submit if endpoint is configured -------
  var form = document.getElementById("tourForm");
  if (form) {
    form.addEventListener("submit", function (e) {
      var action = form.getAttribute("action") || "";
      // If the endpoint is still the placeholder, don't pretend it sent.
      if (action.indexOf("YOUR_FORM_ID") !== -1) {
        e.preventDefault();
        showStatus("Form not connected yet — please use WhatsApp or email for now.", "warn");
        return;
      }
      e.preventDefault();
      var btn = form.querySelector('[type="submit"]');
      var original = btn ? btn.textContent : "";
      if (btn) { btn.disabled = true; btn.textContent = "Sending…"; }
      fetch(action, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" }
      }).then(function (r) {
        if (r.ok) {
          form.reset();
          showStatus("Thank you — your request is on its way. Ivana will reply personally, usually within a few hours.", "ok");
        } else {
          showStatus("Something went wrong. Please reach out on WhatsApp or by email instead.", "warn");
        }
      }).catch(function () {
        showStatus("Something went wrong. Please reach out on WhatsApp or by email instead.", "warn");
      }).finally(function () {
        if (btn) { btn.disabled = false; btn.textContent = original; }
      });
    });
  }
  function showStatus(msg, kind) {
    var box = document.getElementById("formStatus");
    if (!box) return;
    box.textContent = msg;
    box.className = "form-status " + (kind || "");
    box.hidden = false;
  }

  // ---- floating WhatsApp button: lazy-reveal 3s after load ----------------
  var waFloat = document.getElementById("waFloat");
  if (waFloat) {
    window.setTimeout(function () {
      waFloat.hidden = false;
      waFloat.setAttribute("aria-hidden", "false");
      // Force reflow so the transition runs (rAF is paused in background tabs).
      void waFloat.offsetWidth;
      waFloat.classList.add("wa-show");
    }, 3000);
  }

  // ---- current year (footer fallback if not built) ------------------------
  var y = document.querySelector("[data-year]");
  if (y) y.textContent = new Date().getFullYear();
})();
