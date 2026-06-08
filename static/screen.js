const stage = document.getElementById("stage");
const result = document.getElementById("result");
const catHolder = document.getElementById("catHolder");
const catProgress = document.getElementById("catProgress");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const menuBtn = document.getElementById("menuBtn");
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
function seedFooter() {
  seedInfo.textContent = DRAW ? `Seed ${DRAW.rng_seed} · drawn ${DRAW.drawn_at}` : "";
}

/* ---------- Pre-reveal screen ---------- */
function showStart() {
  result.classList.add("hidden");
  stage.classList.remove("hidden");
  if (DRAW && DRAW.categories) {
    stage.innerHTML = `
      <div class="choice">
        <p class="exists">A draw already exists — seed <b>${DRAW.rng_seed}</b>, drawn ${DRAW.drawn_at}.</p>
        <div class="btns">
          <button id="viewBtn" class="primary">View draws</button>
          <button id="redoBtn" class="danger">Re-do draw</button>
          <a id="siteBtn" class="ghost" href="/site/">Go to website</a>
        </div>
      </div>`;
    document.getElementById("viewBtn").onclick = () => openReveal(true);
    document.getElementById("redoBtn").onclick = () => {
      if (confirm("Re-do the official draw? This overwrites the current result.")) draw(true);
    };
  } else {
    stage.innerHTML = `
      <button id="drawBtn" class="draw-btn">DRAW THE HEATS</button>
      <p class="hint">Press once to draw the heat order for all categories.</p>`;
    document.getElementById("drawBtn").onclick = () => draw(false);
  }
  seedFooter();
}

/* ---------- Reveal carousel ---------- */
function openReveal(animate) {
  stage.classList.add("hidden");
  result.classList.remove("hidden");
  cats = ordered(DRAW.categories);
  idx = 0;
  showCat(animate);
  seedFooter();
}

function showCat(animate) {
  const [name, info] = cats[idx];
  const rows = info.teams.map((t, i) => {
    const delay = animate ? (0.15 + i * 0.04).toFixed(2) : "0";
    return `<li style="animation-delay:${delay}s">
      <span class="num">${t.seed}</span>
      <span class="name">${t.team_name || "—"}</span>
      <span class="inst">${t.institution || ""}</span>
    </li>`;
  }).join("");

  catHolder.innerHTML = `
    <section class="cat ${animate ? "anim" : ""}">
      <h2>${name} <small>(${info.team_count} heats)</small></h2>
      <div class="sched">${schedText(info.schedule)}</div>
      <ol>${rows}</ol>
    </section>`;

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
menuBtn.onclick = showStart;
document.addEventListener("keydown", (e) => {
  if (result.classList.contains("hidden")) return;
  if (e.key === "ArrowLeft") step(-1);
  if (e.key === "ArrowRight") step(1);
  if (e.key === "Escape") showStart();
});

/* ---------- Drawing ---------- */
async function draw(force) {
  const url = "/api/draw" + (force ? "?force=1" : "");
  const res = await fetch(url, { method: "POST" });
  if (res.status === 409) { return load(); } // already drawn elsewhere
  DRAW = await res.json();
  openReveal(true);
}

async function load() {
  try { DRAW = await fetch("/api/draw").then((r) => r.json()); }
  catch (e) { DRAW = null; }
  if (DRAW && !DRAW.categories) DRAW = null;
  showStart();
}

load();
