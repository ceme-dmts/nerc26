const stage = document.getElementById("stage");
const result = document.getElementById("result");
const catHolder = document.getElementById("catHolder");
const catProgress = document.getElementById("catProgress");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const seedInfo = document.getElementById("seedInfo");

let DRAW = null;   // current draw data
let cats = [];     // ordered [name, info] pairs
let idx = 0;       // current category index in the reveal

function ordered(categories) {
  return Object.entries(categories).sort((a, b) => {
    const sa = a[1].schedule || {}, sb = b[1].schedule || {};
    return (sa.day || "").localeCompare(sb.day || "") ||
           (sa.time || "").localeCompare(sb.time || "") ||
           a[0].localeCompare(b[0]);
  });
}
function schedText(s) { return s ? `${s.day} · ${s.time} · ${s.venue}` : "Schedule TBD"; }

/* ---------- Start screen: always just the big button ---------- */
function showStart() {
  result.classList.add("hidden");
  stage.classList.remove("hidden");
  seedInfo.textContent = "";
  stage.innerHTML = `
    <button id="drawBtn" class="draw-btn">DRAW THE HEATS</button>
    <p class="hint">Press to draw the heat order for all categories.</p>`;
  document.getElementById("drawBtn").onclick = draw;
}

/* ---------- Reveal carousel ---------- */
function openReveal() {
  stage.classList.add("hidden");
  result.classList.remove("hidden");
  cats = ordered(DRAW.categories);
  idx = 0;
  showCat(true);
  seedInfo.textContent = `Seed ${DRAW.rng_seed} · drawn ${DRAW.drawn_at}`;
}

function row(t, animate, i) {
  const delay = animate ? (0.15 + i * 0.04).toFixed(2) : "0";
  return `<li style="animation-delay:${delay}s">
    <span class="order">${t.seed}</span>
    <span class="tid"><small>Team</small> ${t.team_no || "—"}</span>
    <span class="who"><span class="tname">${t.team_name || "—"}</span>
      <span class="inst">${t.institution || ""}</span></span>
    <span class="rtime">${t.run_time || ""}</span>
  </li>`;
}

const HEAD_ROW = `<li class="head">
    <span class="order">S#</span>
    <span class="tid">Team ID</span>
    <span class="who">Team Name</span>
    <span class="rtime">Expected Time</span>
  </li>`;

function showCat(animate) {
  const [name, info] = cats[idx];
  const rows = info.teams.map((t, i) => row(t, animate, i)).join("");
  catHolder.innerHTML = `
    <section class="cat ${animate ? "anim" : ""}">
      <h2>${name} <small>(${info.team_count} heats)</small></h2>
      <div class="sched">${schedText(info.schedule)}</div>
      <ol>${HEAD_ROW}${rows}</ol>
    </section>`;
  catHolder.scrollTop = 0;  // back to top on each category change
  catProgress.textContent = `${idx + 1} / ${cats.length} · ${name}`;
  prevBtn.disabled = idx === 0;
  nextBtn.disabled = idx === cats.length - 1;
}

function step(delta) {
  const next = idx + delta;
  if (next < 0 || next >= cats.length) return;
  idx = next;
  showCat(true);
}

prevBtn.onclick = () => step(-1);
nextBtn.onclick = () => step(1);
document.addEventListener("keydown", (e) => {
  if (result.classList.contains("hidden")) return;
  if (e.key === "ArrowLeft") step(-1);
  if (e.key === "ArrowRight") step(1);
});

/* ---------- Drawing ---------- */
async function draw() {
  const btn = document.getElementById("drawBtn");
  if (btn) { btn.disabled = true; btn.textContent = "DRAWING…"; }
  DRAW = await fetch("/api/draw", { method: "POST" }).then((r) => r.json());
  openReveal();
}

showStart();
