const state = {
  meta: null,
  plan: null,
  places: [],
};

const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function getJSON(path, params) {
  const url = new URL(path, window.location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  const response = await fetch(url, { headers: { accept: "application/json" } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail && detail.message
        ? `${detail.message} Available: ${(detail.available_dates || []).join(", ")}`
        : `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return body;
}

function fillSelect(node, items, valueKey, labelKey, selected) {
  node.innerHTML = "";
  items.forEach((item) => {
    const option = el("option");
    option.value = typeof item === "string" ? item : item[valueKey];
    option.textContent = typeof item === "string" ? item : item[labelKey];
    if (String(option.value) === String(selected)) option.selected = true;
    node.appendChild(option);
  });
}

function hourOptions(from, to) {
  const out = [];
  for (let hour = from; hour <= to; hour += 1) out.push(`${String(hour).padStart(2, "0")}:00`);
  return out;
}

function currentParams() {
  const measured = $("measured_wbgt").value.trim();
  return {
    place: $("place").value,
    date: $("date").value,
    intensity: $("intensity").value,
    crew: $("crew").value,
    shift_hours: $("shift_hours").value,
    earliest_start: $("earliest_start").value.slice(0, 2),
    latest_start: $("latest_start").value.slice(0, 2),
    exposure: $("exposure").value,
    acclimatised: $("acclimatised").checked ? "true" : "false",
    measured_wbgt: measured === "" ? undefined : measured,
  };
}

const CLASS_COLORS = {
  low: "#4ade80",
  rising: "#fbbf24",
  high: "#fb923c",
  extreme: "#f87171",
};

function drawChart(canvas, hours, limit) {
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.clientWidth || 900;
  const cssHeight = 320;
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const pad = { top: 16, right: 46, bottom: 34, left: 42 };
  const plotW = cssWidth - pad.left - pad.right;
  const plotH = cssHeight - pad.top - pad.bottom;

  const values = hours.map((hour) => hour.wbgt);
  const low = Math.min(...values, limit) - 2;
  const high = Math.max(...values, limit) + 2;
  const span = Math.max(1, high - low);

  const x = (index) =>
    pad.left + (hours.length === 1 ? plotW / 2 : (index / (hours.length - 1)) * plotW);
  const y = (value) => pad.top + plotH - ((value - low) / span) * plotH;

  // Band above the limit.
  const limitY = y(limit);
  ctx.fillStyle = "rgba(239, 68, 68, 0.10)";
  ctx.fillRect(pad.left, pad.top, plotW, Math.max(0, limitY - pad.top));

  // Gridlines and labels.
  ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
  ctx.textBaseline = "middle";
  const step = span > 14 ? 5 : 2;
  const start = Math.ceil(low / step) * step;
  for (let value = start; value <= high; value += step) {
    const gy = y(value);
    ctx.strokeStyle = "rgba(148, 163, 184, 0.14)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.left, gy);
    ctx.lineTo(pad.left + plotW, gy);
    ctx.stroke();
    ctx.fillStyle = "#94a3b8";
    ctx.textAlign = "right";
    ctx.fillText(`${value}`, pad.left - 8, gy);
  }

  // Limit line.
  ctx.strokeStyle = "rgba(239, 68, 68, 0.75)";
  ctx.setLineDash([6, 5]);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(pad.left, limitY);
  ctx.lineTo(pad.left + plotW, limitY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Area under the curve.
  const gradient = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
  gradient.addColorStop(0, "rgba(245, 158, 11, 0.28)");
  gradient.addColorStop(1, "rgba(245, 158, 11, 0.02)");
  ctx.beginPath();
  hours.forEach((hour, index) => {
    const px = x(index);
    const py = y(hour.wbgt);
    if (index === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.lineTo(x(hours.length - 1), pad.top + plotH);
  ctx.lineTo(x(0), pad.top + plotH);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Line.
  ctx.beginPath();
  hours.forEach((hour, index) => {
    const px = x(index);
    const py = y(hour.wbgt);
    if (index === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.strokeStyle = "#f59e0b";
  ctx.lineWidth = 2.4;
  ctx.stroke();

  // Points.
  hours.forEach((hour, index) => {
    ctx.beginPath();
    ctx.arc(x(index), y(hour.wbgt), 3.4, 0, Math.PI * 2);
    ctx.fillStyle = CLASS_COLORS[hour.class] || "#f59e0b";
    ctx.fill();
    ctx.strokeStyle = "#0e1116";
    ctx.lineWidth = 1.2;
    ctx.stroke();
  });

  // X labels.
  ctx.fillStyle = "#94a3b8";
  ctx.textAlign = "center";
  const everyN = hours.length > 10 ? 2 : 1;
  hours.forEach((hour, index) => {
    if (index % everyN !== 0 && index !== hours.length - 1) return;
    ctx.fillText(hour.label, x(index), cssHeight - 14);
  });

  // End label for the limit.
  ctx.fillStyle = "#fca5a5";
  ctx.textAlign = "left";
  ctx.fillText(`${limit.toFixed(1)} C limit`, pad.left + plotW + 6, limitY);
}

function renderStrip(hours) {
  const strip = $("strip");
  strip.innerHTML = "";
  strip.style.gridTemplateColumns = `repeat(${hours.length}, minmax(0, 1fr))`;
  hours.forEach((hour) => {
    const cell = el("div", "strip-cell");
    cell.style.background = CLASS_COLORS[hour.class] || "#f59e0b";
    cell.title = `${hour.label}: WBGT ${hour.wbgt} C, work ${hour.work_min} min`;
    cell.appendChild(document.createTextNode(`${hour.work_min}m`));
    cell.appendChild(el("span", null, hour.label));
    strip.appendChild(cell);
  });
}

function renderTable(hours) {
  const body = $("table").querySelector("tbody");
  body.innerHTML = "";
  hours.forEach((hour) => {
    const row = document.createElement("tr");
    const cells = [
      hour.label,
      `${hour.temp_c.toFixed(1)} °C`,
      `${Math.round(hour.rh)} %`,
      `${Math.round(hour.shortwave_wm2)} W/m²`,
      `${hour.wbgt.toFixed(1)}`,
      `${hour.work_min} min`,
      `${hour.rest_min} min`,
      `${hour.water_l.toFixed(1)} L`,
    ];
    cells.forEach((text, index) => {
      const cell = el("td", index === 0 ? "" : "num", text);
      row.appendChild(cell);
    });
    const reasonCell = document.createElement("td");
    const pill = el("span", `pill ${hour.class}`, hour.class);
    reasonCell.appendChild(pill);
    reasonCell.appendChild(document.createTextNode(` ${hour.reason}`));
    row.appendChild(reasonCell);
    body.appendChild(row);
  });
}

function renderCrewCard(document_) {
  const plan = document_.plan;
  const place = document_.place;
  $("crew-title").textContent = `${place.name}${place.state ? ", " + place.state : ""} — ${plan.date}`;
  $("crew-meta").innerHTML = "";
  $("crew-meta").appendChild(el("div", null, `${plan.start} to ${plan.finish}`));
  $("crew-meta").appendChild(el("div", null, `${plan.shift_hours} hour shift`));

  const summary = $("crew-summary");
  summary.innerHTML = "";
  const items = [
    ["Intensity", plan.intensity],
    ["Crew", `${plan.crew} people`],
    ["Peak WBGT", `${plan.totals.peak_wbgt.toFixed(1)} C at ${plan.totals.peak_time}`],
    ["Continuous limit", `${plan.limit_c.toFixed(1)} C`],
    ["Work", `${plan.totals.work_hours} h`],
    ["Rest", `${plan.totals.rest_hours} h`],
    ["Water per worker", `${plan.totals.water_per_worker_l} L`],
    ["Water for crew", `${plan.totals.water_crew_l} L`],
  ];
  items.forEach(([label, value]) => {
    const box = document.createElement("div");
    box.appendChild(el("dt", null, label));
    box.appendChild(el("dd", null, value));
    summary.appendChild(box);
  });

  const strip = $("crew-hours");
  strip.innerHTML = "";
  strip.style.gridTemplateColumns = `repeat(${plan.hours.length}, minmax(0, 1fr))`;
  plan.hours.forEach((hour) => {
    const cell = document.createElement("div");
    cell.appendChild(el("b", null, hour.label));
    cell.appendChild(document.createTextNode(`${hour.work_min}/${hour.rest_min}`));
    strip.appendChild(cell);
  });

  const notes = $("crew-notes");
  notes.innerHTML = "";
  notes.appendChild(el("li", null, plan.recommendation));
  (plan.warnings || []).forEach((warning) => notes.appendChild(el("li", null, warning)));
  notes.appendChild(
    el(
      "li",
      null,
      "Work/rest pairs are minutes of work and rest in each hour. Drink to thirst, and add electrolytes for long shifts."
    )
  );
}

function render(document_) {
  const plan = document_.plan;
  const data = document_.data || {};
  state.plan = document_;

  $("empty").hidden = true;
  $("output").hidden = false;
  delete $("output").dataset.error;

  const badge = $("data-badge");
  const mode = data.mode || "unknown";
  badge.className = `badge ${mode === "live" || mode === "cache" ? "live" : "snapshot"}`;
  badge.textContent =
    mode === "live"
      ? "Live forecast"
      : mode === "cache"
      ? "Cached forecast"
      : mode === "snapshot"
      ? "Bundled snapshot"
      : mode;

  const banner = $("banner");
  banner.innerHTML = "";
  const head = document.createElement("div");
  head.innerHTML = `<strong>${plan.start}</strong> start. ${plan.recommendation}`;
  banner.appendChild(head);
  (plan.warnings || []).forEach((warning) => banner.appendChild(el("div", "warn", warning)));
  if (data.note) banner.appendChild(el("div", "warn", data.note));

  $("card-window").textContent = `${plan.start} – ${plan.finish}`;
  $("card-window-note").textContent = `${plan.shift_hours} h, ${plan.intensity} work`;
  $("card-peak").textContent = `${plan.totals.peak_wbgt.toFixed(1)} °C`;
  $("card-peak-note").textContent = `at ${plan.totals.peak_time}, limit ${plan.limit_c.toFixed(1)} °C`;
  $("card-work").textContent = `${plan.totals.work_hours} h work`;
  $("card-work-note").textContent = `${plan.totals.rest_hours} h rest in the shift`;
  $("card-water").textContent = `${plan.totals.water_per_worker_l} L`;
  $("card-water-note").textContent = `${plan.totals.water_crew_l} L for ${plan.crew} people`;

  $("legend-limit").textContent = `${plan.limit_c.toFixed(1)} °C`;
  drawChart($("chart"), plan.hours, plan.limit_c);
  renderStrip(plan.hours);
  renderTable(plan.hours);
  renderCrewCard(document_);

  const measured = $("measured-panel");
  if (plan.measured) {
    measured.hidden = false;
    $("measured-text").textContent = plan.measured.note;
  } else {
    measured.hidden = true;
  }

  $("csv").href = `/api/plan.csv?${new URLSearchParams(currentParams()).toString()}`;
  $("source").textContent = `Source: ${data.source || "Open-Meteo"} — ${
    data.note || ""
  } Fetched ${data.fetched_at || "unknown"}.`;
}

async function submit(event) {
  if (event) event.preventDefault();
  const button = $("submit");
  button.disabled = true;
  button.textContent = "Building…";
  try {
    const params = currentParams();
    const document_ = await getJSON("/api/plan", params);
    if (!params.date) {
      fillSelect($("date"), document_.available_dates, null, null, document_.date);
    }
    render(document_);
  } catch (error) {
    $("empty").hidden = true;
    $("output").hidden = false;
    $("output").dataset.error = "1";
    const banner = $("banner");
    banner.innerHTML = "";
    banner.className = "banner";
    banner.appendChild(el("strong", null, "Could not build the plan. "));
    banner.appendChild(document.createTextNode(error.message));
  } finally {
    button.disabled = false;
    button.textContent = "Build the shift plan";
  }
}

function applyUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const map = {
    place: "place",
    date: "date",
    intensity: "intensity",
    crew: "crew",
    shift_hours: "shift_hours",
    earliest_start: "earliest_start",
    latest_start: "latest_start",
    exposure: "exposure",
    measured_wbgt: "measured_wbgt",
  };
  Object.entries(map).forEach(([key, id]) => {
    if (!params.has(key)) return;
    const node = $(id);
    if (!node) return;
    let value = params.get(key);
    if (key === "earliest_start" || key === "latest_start") {
      value = `${String(Number(value)).padStart(2, "0")}:00`;
    }
    node.value = value;
  });
  if (params.has("acclimatised")) {
    $("acclimatised").checked = params.get("acclimatised") !== "false";
  }
}

async function init() {
  try {
    const meta = await getJSON("/api/meta");
    state.meta = meta;
    fillSelect(
      $("intensity"),
      meta.intensities,
      "id",
      "label",
      meta.defaults.intensity
    );
    $("crew").value = meta.defaults.crew;
    $("shift_hours").value = meta.defaults.shift_hours;
    fillSelect($("earliest_start"), hourOptions(0, 23), null, null, "05:00");
    fillSelect($("latest_start"), hourOptions(0, 23), null, null, "14:00");
  } catch (error) {
    $("data-badge").textContent = "API unavailable";
  }

  try {
    const places = await getJSON("/api/places");
    state.places = places.places;
    fillSelect($("place"), places.places, "id", "name", "cherrybrook");
  } catch (error) {
    $("place").innerHTML = "<option value=''>Unavailable</option>";
  }

  $("plan-form").addEventListener("submit", submit);
  $("print").addEventListener("click", () => window.print());
  window.addEventListener("resize", () => {
    if (state.plan) drawChart($("chart"), state.plan.plan.hours, state.plan.plan.limit_c);
  });

  applyUrlParams();
  await submit();
}

init();