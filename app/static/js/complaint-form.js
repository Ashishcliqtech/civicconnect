// Client-side validation for the complaint form (the server validates again).
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("complaint-form");
  if (!form) return;
  const maxBytes = Number(form.dataset.maxMb || 5) * 1024 * 1024;
  const desc = form.querySelector("textarea[name=description]");
  const count = document.getElementById("desc-count");
  const photo = form.querySelector("input[type=file]");
  const preview = document.getElementById("photo-preview");

  const updateCount = () => { count.textContent = `${desc.value.length}/2000 characters (min 20)`; };
  desc.addEventListener("input", updateCount); updateCount();

  photo.addEventListener("change", () => {
    const f = photo.files[0];
    photo.setCustomValidity("");
    preview.hidden = true;
    if (!f) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(f.type)) photo.setCustomValidity("Please choose a JPEG, PNG or WebP image.");
    else if (f.size > maxBytes) photo.setCustomValidity("Image is too large.");
    else { preview.src = URL.createObjectURL(f); preview.hidden = false; }
    photo.reportValidity();
  });

  form.addEventListener("submit", (e) => {
    const errors = [];
    if (form.elements.title.value.trim().length < 5) errors.push("Title must be at least 5 characters.");
    if (desc.value.trim().length < 20) errors.push("Description must be at least 20 characters.");
    if (form.elements.latitude.value === "" || form.elements.longitude.value === "") errors.push("Please choose a location on the map or enter coordinates.");
    if (errors.length) { e.preventDefault(); e.stopImmediatePropagation(); alert(errors.join("\n")); }
  }, true);
});
