const stage = document.getElementById("stage");
const drawBtn = document.getElementById("drawBtn");
const result = document.getElementById("result");
const seedInfo = document.getElementById("seedInfo");
const redoBtn = document.getElementById("redoBtn");

// Order categories by schedule (Day, then time), falling back to name.
function ordered(categories) {
  return Object.entries(categories).sort((a, b) => {
    const sa = a[1].schedule || {}, sb = b[1].schedule || {};
    return (sa.day || "").localeCompare(sb.day || "") ||
           (sa.time || "").localeCompare(sb.time || "") ||
           a[0].localeCompare(b[0]);
  });
}

function render(data, animate) {
  stage.classList.add("hidden");
  result.classList.remove("hidden");
  result.innerHTML = "";

  ordered(data.categories).forEach(([name, info], ci) => {
    const sch = info.schedule;
    const schedLine = sch
      ? `${sch.day} · ${sch.time} · ${sch.venue}`
      : "Schedule TBD";

    const panel = document.createElement("section");
    panel.className = "cat";
    panel.style.animationDelay = animate ? `${ci * 0.25}s` : "0s";

    const rows = info.teams.map((t, i) => {
      const delay = animate ? (ci * 0.25 + 0.4 + i * 0.05).toFixed(2) : "0";
      return `<li style="animation-delay:${delay}s">
        <span class="num">${t.seed}</span>
        <span class="name">${t.team_name || "—"}</span>
        <span class="inst">${t.institution || ""}</span>
      </li>`;
    }).join("");

    panel.innerHTML = `
      <h2>${name} <small style="color:var(--muted);font-size:.9rem">(${info.team_count})</small></h2>
      <div class="sched">${schedLine}</div>
      <ol>${rows}</ol>`;
    result.appendChild(panel);
  });

  seedInfo.textContent = `Seed ${data.rng_seed} · drawn ${data.drawn_at}`;
  redoBtn.classList.remove("hidden");
}

async function draw(force) {
  drawBtn.disabled = true;
  drawBtn.textContent = "DRAWING…";
  const url = "/api/draw" + (force ? "?force=1" : "");
  const res = await fetch(url, { method: "POST" });
  if (res.status === 409) {
    // Already drawn elsewhere — just show the existing result.
    return load();
  }
  const data = await res.json();
  render(data, true);
}

async function load() {
  const data = await fetch("/api/draw").then((r) => r.json());
  if (data && data.categories) {
    render(data, false); // already drawn: show without replaying animation
  }
}

drawBtn.addEventListener("click", () => draw(false));
redoBtn.addEventListener("click", () => {
  if (confirm("Redo the official draw? This overwrites the current result.")) {
    draw(true);
  }
});

load();
