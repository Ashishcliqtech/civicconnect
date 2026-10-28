// Shared UI behaviour: icons, nav toggle, toasts, confirm dialogs, submit loading state.
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();

  const toggle = document.querySelector(".nav-toggle");
  const links = document.getElementById("nav-links");
  if (toggle) toggle.addEventListener("click", () => {
    const open = links.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });

  document.querySelectorAll(".toast").forEach((t) => {
    t.querySelector(".toast-close").addEventListener("click", () => t.remove());
    setTimeout(() => t.remove(), 7000);
  });

  // Confirmation dialog for forms carrying data-confirm="message"
  const dialog = document.getElementById("confirm-dialog");
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (form.dataset.confirmed) return;
      e.preventDefault();
      document.getElementById("confirm-text").textContent = form.dataset.confirm;
      dialog.addEventListener("close", function handler() {
        dialog.removeEventListener("close", handler);
        if (dialog.returnValue === "ok") { form.dataset.confirmed = "1"; form.requestSubmit(); }
      });
      dialog.showModal();
    });
  });

  // Loading state: prevent double submits
  document.querySelectorAll("form[data-loading]").forEach((form) => {
    form.addEventListener("submit", () => {
      if (!form.checkValidity || form.checkValidity()) {
        const btn = form.querySelector("button[type=submit]");
        if (btn) { btn.disabled = true; btn.textContent = "Please wait…"; }
      }
    });
  });
});
