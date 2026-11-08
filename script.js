/* paulcheenis — lightbox, gentle reveals, nothing clever. */
(function () {
  "use strict";

  /* ---------- lightbox ---------- */
  var box = document.createElement("div");
  box.className = "lightbox";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  box.setAttribute("aria-label", "Image viewer");
  box.dataset.open = "false";
  box.innerHTML =
    '<div class="lightbox__bar">' +
      '<span data-count></span>' +
      '<button type="button" data-close>close ✕</button>' +
    '</div>' +
    '<div class="lightbox__stage"><img alt=""></div>' +
    '<div class="lightbox__nav">' +
      '<button type="button" data-prev>← prev</button>' +
      '<button type="button" data-next>next →</button>' +
    '</div>';
  document.body.appendChild(box);

  var stageImg = box.querySelector("img");
  var counter = box.querySelector("[data-count]");
  var items = [];
  var index = 0;
  var lastFocus = null;

  function collect() {
    items = Array.prototype.slice.call(document.querySelectorAll("[data-zoom]"));
  }

  function show(i) {
    if (!items.length) return;
    index = (i + items.length) % items.length;
    var el = items[index];
    var full = el.getAttribute("data-zoom") || el.getAttribute("href") || "";
    var img = el.querySelector("img");
    stageImg.src = full;
    stageImg.alt = img ? (img.alt || "") : "";
    counter.textContent = (index + 1) + " / " + items.length +
      (el.getAttribute("data-label") ? " · " + el.getAttribute("data-label") : "");
  }

  function open(i) {
    collect();
    lastFocus = document.activeElement;
    box.dataset.open = "true";
    document.documentElement.style.overflow = "hidden";
    show(i);
    box.querySelector("[data-close]").focus();
  }

  function close() {
    box.dataset.open = "false";
    stageImg.removeAttribute("src");
    document.documentElement.style.overflow = "";
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener("click", function (ev) {
    var target = ev.target.closest("[data-zoom]");
    if (target) {
      ev.preventDefault();
      collect();
      open(items.indexOf(target));
      return;
    }
    if (ev.target.closest("[data-close]")) return close();
    if (ev.target.closest("[data-prev]")) return show(index - 1);
    if (ev.target.closest("[data-next]")) return show(index + 1);
    if (ev.target === box) return close();
  });

  document.addEventListener("keydown", function (ev) {
    if (box.dataset.open !== "true") return;
    if (ev.key === "Escape") close();
    if (ev.key === "ArrowLeft") show(index - 1);
    if (ev.key === "ArrowRight") show(index + 1);
  });

  /* ---------- reveal on scroll ---------- */
  var targets = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && targets.length) {
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          obs.unobserve(e.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    targets.forEach(function (t) { obs.observe(t); });
  } else {
    targets.forEach(function (t) { t.classList.add("is-in"); });
  }

  /* ---------- year ---------- */
  var yr = document.querySelector("[data-year]");
  if (yr) yr.textContent = new Date().getFullYear();
})();
