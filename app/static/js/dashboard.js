// Builds Chart.js charts from <canvas data-chart='{...}'> elements (data comes from the database).
document.addEventListener("DOMContentLoaded", () => {
  if (!window.Chart) return;
  const palette = ["#1f6feb", "#0f8a5f", "#f5b301", "#e5484d", "#7c3aed", "#0b2545", "#14b8a6", "#f97316"];
  document.querySelectorAll("canvas[data-chart]").forEach((canvas) => {
    const cfg = JSON.parse(canvas.dataset.chart);
    if (!cfg.values.length) { canvas.parentElement.style.display = "none"; return; }
    const round = cfg.type === "doughnut";
    new Chart(canvas, {
      type: cfg.type,
      data: { labels: cfg.labels, datasets: [{ label: cfg.label, data: cfg.values,
        backgroundColor: round ? palette : cfg.color + "cc", borderColor: round ? "#fff" : cfg.color,
        tension: .3, fill: cfg.type === "line" }] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: round, position: "bottom" } },
        scales: round ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  });
});
