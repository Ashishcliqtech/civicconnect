// Leaflet maps: location picker (complaint form), read-only detail map, and public map.
// Tiles come from OpenStreetMap. Geocoding uses OSM Nominatim; manual coordinates are always available.
document.addEventListener("DOMContentLoaded", () => {
  if (!window.L) return; // Leaflet CDN blocked/offline: the manual coordinate inputs still work.
  const DEFAULT = [28.6139, 77.209]; // fallback centre; change for your city
  const tiles = () => L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" });

  // 1) Picker
  const pickerEl = document.getElementById("picker-map");
  if (pickerEl) {
    const latIn = document.getElementById("latitude"), lngIn = document.getElementById("longitude");
    const addr = document.getElementById("address");
    const hasCoords = latIn.value !== "" && lngIn.value !== "";
    const start = hasCoords ? [parseFloat(latIn.value), parseFloat(lngIn.value)] : DEFAULT;
    const map = L.map(pickerEl).setView(start, hasCoords ? 16 : 12);
    tiles().addTo(map);
    let marker = null;
    const setPoint = (lat, lng, pan) => {
      latIn.value = lat.toFixed(6); lngIn.value = lng.toFixed(6);
      if (!marker) {
        marker = L.marker([lat, lng], { draggable: true }).addTo(map);
        marker.on("dragend", () => { const p = marker.getLatLng(); setPoint(p.lat, p.lng, false); });
      } else marker.setLatLng([lat, lng]);
      if (pan) map.setView([lat, lng], Math.max(map.getZoom(), 16));
    };
    if (hasCoords) setPoint(start[0], start[1], false);
    map.on("click", (e) => setPoint(e.latlng.lat, e.latlng.lng, false));
    const syncFromInputs = () => {
      const la = parseFloat(latIn.value), ln = parseFloat(lngIn.value);
      if (!isNaN(la) && !isNaN(ln) && Math.abs(la) <= 90 && Math.abs(ln) <= 180) setPoint(la, ln, true);
    };
    latIn.addEventListener("change", syncFromInputs); lngIn.addEventListener("change", syncFromInputs);

    document.getElementById("geocode-btn").addEventListener("click", async () => {
      if (!addr.value.trim()) return;
      try {
        const res = await fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(addr.value));
        const data = await res.json();
        if (data.length) setPoint(parseFloat(data[0].lat), parseFloat(data[0].lon), true);
        else alert("Address not found. Click the map or enter coordinates manually.");
      } catch (err) { alert("Address search is unavailable. Click the map or enter coordinates manually."); }
    });
    document.getElementById("locate-btn").addEventListener("click", () => {
      if (!navigator.geolocation) return alert("Geolocation is not supported by your browser.");
      navigator.geolocation.getCurrentPosition((p) => setPoint(p.coords.latitude, p.coords.longitude, true),
        () => alert("Could not get your location. Click the map instead."));
    });
  }

  // 2) Read-only detail map
  const detailEl = document.getElementById("detail-map");
  if (detailEl) {
    const pos = [parseFloat(detailEl.dataset.lat), parseFloat(detailEl.dataset.lng)];
    const m = L.map(detailEl, { scrollWheelZoom: false }).setView(pos, 16);
    tiles().addTo(m); L.marker(pos).addTo(m);
  }

  // 3) Public map (privacy-safe rounded coordinates from the API)
  const publicEl = document.getElementById("public-map");
  if (publicEl) {
    const m = L.map(publicEl).setView(DEFAULT, 11);
    tiles().addTo(m);
    fetch(publicEl.dataset.api + "?" + publicEl.dataset.query).then((r) => r.json()).then((items) => {
      const pts = [];
      items.forEach((c) => {
        const mk = L.marker([c.lat, c.lng]).addTo(m);
        const div = document.createElement("div"); // textContent avoids XSS in popups
        const b = document.createElement("strong"); b.textContent = c.title;
        div.append(b, document.createElement("br"), document.createTextNode(`${c.category} · ${c.status} · ${c.date}`));
        mk.bindPopup(div); pts.push([c.lat, c.lng]);
      });
      if (pts.length) m.fitBounds(pts, { padding: [30, 30], maxZoom: 15 });
    }).catch(() => {});
  }
});
