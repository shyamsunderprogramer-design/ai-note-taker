(() => {
  "use strict";
  const menuButton = document.querySelector(".menu-toggle");
  const menu = document.querySelector("#site-navigation");
  const desktop = window.matchMedia("(min-width: 851px)");
  function closeMenu(restoreFocus = false) {
    menu.classList.remove("is-open");
    menuButton.setAttribute("aria-expanded", "false");
    if (restoreFocus) menuButton.focus();
  }
  menuButton.addEventListener("click", () => {
    const opened = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!opened));
    menu.classList.toggle("is-open", !opened);
  });
  menu.addEventListener("click", (event) => {
    if (event.target.closest("a")) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menuButton.getAttribute("aria-expanded") === "true")
      closeMenu(true);
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".nav-shell")) closeMenu();
  });
  desktop.addEventListener("change", () => closeMenu());

  const tabs = [...document.querySelectorAll("[data-example]")];
  function selectExample(name, { focus = false, updateURL = false } = {}) {
    const selected = tabs.find((tab) => tab.dataset.example === name) || tabs[0];
    for (const tab of tabs) {
      const active = tab === selected;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      document.getElementById(tab.getAttribute("aria-controls")).hidden = !active;
    }
    if (focus) selected.focus();
    if (updateURL) {
      const url = new URL(window.location.href);
      const value = selected.dataset.example;
      if ((url.searchParams.get("example") || "meeting") !== value) {
        if (value === "meeting") url.searchParams.delete("example");
        else url.searchParams.set("example", value);
        window.history.pushState(null, "", url);
      }
    }
  }
  for (const [index, tab] of tabs.entries()) {
    tab.addEventListener("click", () => selectExample(tab.dataset.example, { updateURL: true }));
    tab.addEventListener("keydown", (event) => {
      let target;
      if (event.key === "ArrowRight") target = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") target = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") target = 0;
      if (event.key === "End") target = tabs.length - 1;
      if (target === undefined) return;
      event.preventDefault();
      selectExample(tabs[target].dataset.example, { focus: true, updateURL: true });
    });
  }
  document.querySelectorAll("[data-show-example]").forEach((link) => {
    link.addEventListener("click", () =>
      selectExample(link.dataset.showExample, { updateURL: true }),
    );
  });
  const readExample = () =>
    selectExample(new URL(window.location.href).searchParams.get("example"));
  window.addEventListener("popstate", readExample);
  readExample();
})();
