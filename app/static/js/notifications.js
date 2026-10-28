// Polls the unread-notification count every 60 seconds and updates the bell badge.
(function () {
  const url = document.currentScript.dataset.url;
  const badge = document.getElementById("notif-badge");
  if (!url || !badge) return;
  async function refresh() {
    try {
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (!res.ok) return;
      const { unread } = await res.json();
      badge.textContent = unread;
      badge.hidden = unread === 0;
    } catch (e) { /* offline: ignore */ }
  }
  setInterval(refresh, 60000);
})();
