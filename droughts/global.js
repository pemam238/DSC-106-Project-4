/* droughts/global.js
   D3-powered drought visualisation.
   Requires D3 v7 loaded before this script.
*/

// ── DATA ─────────────────────────────────────────────────────────────────────
const CONTINENTS = [
    {
      name: "South America",
      spi_change: -0.1776,
      variability_change: 0.0016,
      drought_change: 0.0509,
      slope_change: 0.0053,
      baseline_spi: 0.0545,
      modern_spi: -0.1231,
      hero: true,
    },
    {
      name: "Africa",
      spi_change: -0.0206,
      variability_change: -0.0329,
      drought_change: 0.0293,
      slope_change: 0.0002,
      baseline_spi: 0.0053,
      modern_spi: -0.0152,
    },
    {
      name: "Asia",
      spi_change: 0.2445,
      variability_change: 0.0098,
      drought_change: -0.0430,
      slope_change: 0.0071,
      baseline_spi: -0.0529,
      modern_spi: 0.1916,
    },
    {
      name: "Europe",
      spi_change: 0.1728,
      variability_change: -0.0114,
      drought_change: -0.0317,
      slope_change: 0.0110,
      baseline_spi: -0.0183,
      modern_spi: 0.1545,
    },
    {
      name: "North America",
      spi_change: 0.0987,
      variability_change: 0.0128,
      drought_change: -0.0195,
      slope_change: -0.0067,
      baseline_spi: -0.0046,
      modern_spi: 0.0941,
    },
    {
      name: "Antarctica",
      spi_change: 0.3833,
      variability_change: 0.0362,
      drought_change: -0.0605,
      slope_change: 0.0061,
      baseline_spi: -0.0678,
      modern_spi: 0.3155,
    },
    {
      name: "Australia-Oceania",
      spi_change: -0.0077,
      variability_change: -0.0379,
      drought_change: 0.0116,
      slope_change: -0.0018,
      baseline_spi: -0.0006,
      modern_spi: -0.0084,
    },
  ];
  
  // ── COLOR SCALES ──────────────────────────────────────────────────────────────
  const spiColorScale = d3.scaleLinear()
    .domain([-0.22, 0, 0.42])
    .range(["#c47a3a", "#d4c9b8", "#2e7d9e"])
    .clamp(true);
  
  const droughtColorScale = d3.scaleLinear()
    .domain([-0.07, 0, 0.06])
    .range(["#2e7d9e", "#d4c9b8", "#7a3b1e"])
    .clamp(true);
  
  // ── CRACK GENERATOR ───────────────────────────────────────────────────────────
  // Produces SVG path data for a crack emanating from a point
  function generateCrack(x, y, angle, length, branchDepth, variability, rng) {
    const paths = [];
    const jagged = 0.3 + Math.abs(variability) * 8;
  
    function crack(cx, cy, ang, len, depth) {
      if (len < 4 || depth < 0) return;
      const segments = Math.floor(4 + rng() * 3);
      let px = cx, py = cy;
      let pathD = `M ${px} ${py}`;
      const segLen = len / segments;
  
      for (let i = 0; i < segments; i++) {
        const jitter = (rng() - 0.5) * jagged * 2;
        const nx = px + Math.cos(ang + jitter) * segLen;
        const ny = py + Math.sin(ang + jitter) * segLen;
        pathD += ` L ${nx.toFixed(1)} ${ny.toFixed(1)}`;
        px = nx; py = ny;
      }
      paths.push({ d: pathD, depth });
  
      // branching probability scales with variability magnitude
      const branchProb = 0.35 + Math.abs(variability) * 4;
      if (rng() < branchProb && depth > 0) {
        const branchAngle = ang + (rng() > 0.5 ? 1 : -1) * (0.4 + rng() * 0.5);
        crack(px - segLen * 0.3, py - segLen * 0.3, branchAngle, len * 0.55, depth - 1);
      }
    }
  
    crack(x, y, angle, length, branchDepth);
    return paths;
  }
  
  // Seeded simple random (mulberry32)
  function seededRng(seed) {
    let s = seed;
    return () => {
      s |= 0; s = s + 0x6D2B79F5 | 0;
      let t = Math.imul(s ^ s >>> 15, 1 | s);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  
  // ── PLATE CARD BUILDER ────────────────────────────────────────────────────────
  function buildPlateCard(d, index) {
    const card = document.createElement("div");
    card.className = "plate-card";
    card.style.animationDelay = `${index * 0.08}s`;
  
    // stat formatting
    const spiSign  = d.spi_change >= 0 ? "+" : "";
    const drtSign  = d.drought_change >= 0 ? "+" : "";
    const spiClass = d.spi_change >= 0 ? "wetting" : "drying";
    const drtClass = d.drought_change > 0 ? "drying" : "wetting";
  
    card.innerHTML = `
      <div class="plate-name">${d.name}</div>
      <div class="plate-svg-wrap">
        <svg viewBox="0 0 240 140" id="plate-svg-${index}"></svg>
      </div>
      <div class="plate-stats">
        <div class="plate-stat-item">
          <span class="plate-stat-val ${spiClass}">${spiSign}${d.spi_change.toFixed(3)}</span>
          <span class="plate-stat-label">SPI change</span>
        </div>
        <div class="plate-stat-item">
          <span class="plate-stat-val ${drtClass}">${drtSign}${(d.drought_change * 100).toFixed(1)}pp</span>
          <span class="plate-stat-label">Drought freq Δ</span>
        </div>
      </div>
    `;
    return card;
  }
  
  function renderPlateSvg(d, svgEl, W, H) {
    const svg = d3.select(svgEl);
    const rng = seededRng(d.name.charCodeAt(0) * 31 + d.name.charCodeAt(2));
  
    // background tile fill
    const fillColor = spiColorScale(d.spi_change);
    svg.append("rect")
      .attr("x", 0).attr("y", 0)
      .attr("width", W).attr("height", H)
      .attr("fill", fillColor)
      .attr("rx", 1);
  
    // grain texture overlay via lines
    const grainGroup = svg.append("g").attr("opacity", 0.07);
    for (let i = 0; i < 20; i++) {
      const y = rng() * H;
      grainGroup.append("line")
        .attr("x1", 0).attr("y1", y)
        .attr("x2", W).attr("y2", y)
        .attr("stroke", "#1c1410").attr("stroke-width", 0.5);
    }
  
    // cracks — only if drought is increasing
    if (d.drought_change > 0.005) {
      const crackCount = Math.max(2, Math.round(d.drought_change * 60));
      const maxCrackLen = 20 + d.drought_change * 300;
      const strokeBase = 0.5 + d.drought_change * 12;
  
      const crackGroup = svg.append("g");
  
      for (let c = 0; c < crackCount; c++) {
        const cx = rng() * W;
        const cy = rng() * H;
        const angle = rng() * Math.PI * 2;
        const len = maxCrackLen * (0.5 + rng() * 0.5);
        const branchDepth = 1 + Math.floor(Math.abs(d.variability_change) * 60);
        const paths = generateCrack(cx, cy, angle, len, Math.min(branchDepth, 3), d.variability_change, seededRng(c * 137 + d.name.charCodeAt(0)));
  
        paths.forEach(({ d: pathD, depth }) => {
          crackGroup.append("path")
            .attr("d", pathD)
            .attr("stroke", "#3d1f0a")
            .attr("stroke-width", strokeBase / (depth + 1))
            .attr("stroke-linecap", "round")
            .attr("fill", "none")
            .attr("opacity", 0.7 / (depth * 0.4 + 1));
        });
      }
    }
  
    // slope arrow (momentum indicator)
    const arrowX = W - 18;
    const arrowY = H - 14;
    const arrowUp = d.slope_change > 0; // positive slope = wetter trend
    const arrowColor = arrowUp ? "#2e7d9e" : "#c47a3a";
    svg.append("text")
      .attr("x", arrowX).attr("y", arrowY)
      .attr("text-anchor", "middle")
      .attr("font-size", 12)
      .attr("fill", arrowColor)
      .attr("opacity", 0.8)
      .text(arrowUp ? "↑" : "↓");
  }
  
  // ── STORY SVG BUILDERS ────────────────────────────────────────────────────────
  function buildStorySvg(svgId, dataEntry, isCracked) {
    const el = document.getElementById(svgId);
    if (!el) return;
    const W = 300, H = 400;
    const svg = d3.select(el);
    const rng = seededRng(dataEntry.name.charCodeAt(0) * 97);
  
    const fillColor = spiColorScale(dataEntry.spi_change);
    svg.append("rect").attr("x", 0).attr("y", 0).attr("width", W).attr("height", H)
      .attr("fill", fillColor).attr("rx", 3);
  
    // grain
    const grainG = svg.append("g").attr("opacity", 0.06);
    for (let i = 0; i < 40; i++) {
      const y = rng() * H;
      grainG.append("line").attr("x1", 0).attr("y1", y).attr("x2", W).attr("y2", y)
        .attr("stroke", "#1c1410").attr("stroke-width", 0.6);
    }
  
    if (isCracked) {
      const crackCount = Math.round(dataEntry.drought_change * 100);
      const maxLen = 40 + dataEntry.drought_change * 500;
      const sw = 1.2 + dataEntry.drought_change * 18;
      const cg = svg.append("g");
  
      for (let c = 0; c < crackCount; c++) {
        const cx = rng() * W;
        const cy = rng() * H;
        const angle = rng() * Math.PI * 2;
        const len = maxLen * (0.5 + rng() * 0.5);
        const bd = 2;
        const paths = generateCrack(cx, cy, angle, len, bd, dataEntry.variability_change,
          seededRng(c * 211 + dataEntry.name.charCodeAt(1)));
        paths.forEach(({ d, depth }) => {
          cg.append("path").attr("d", d)
            .attr("stroke", "#3d1f0a")
            .attr("stroke-width", sw / (depth + 1))
            .attr("stroke-linecap", "round")
            .attr("fill", "none")
            .attr("opacity", 0.75 / (depth * 0.4 + 1));
        });
      }
    }
  
    // label
    svg.append("text")
      .attr("x", 16).attr("y", H - 16)
      .attr("font-family", "'DM Mono', monospace")
      .attr("font-size", 9)
      .attr("letter-spacing", "0.15em")
      .attr("fill", "rgba(28,20,16,0.5)")
      .text(dataEntry.name.toUpperCase());
  }
  
  // ── SCROLL REVEAL ─────────────────────────────────────────────────────────────
  function initScrollReveal() {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.classList.add("visible");
            observer.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    document.querySelectorAll(".reveal-section").forEach(el => observer.observe(el));
  }
  
  // ── INIT ──────────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
  
    // Build plate cards
    const grid = document.getElementById("plates-grid");
    if (grid) {
      CONTINENTS.forEach((d, i) => {
        const card = buildPlateCard(d, i);
        grid.appendChild(card);
        // render SVG after card is in DOM
        requestAnimationFrame(() => {
          const svgEl = document.getElementById(`plate-svg-${i}`);
          if (svgEl) renderPlateSvg(d, svgEl, 240, 140);
        });
      });
    }
  
    // Build story SVGs
    const sa = CONTINENTS.find(c => c.name === "South America");
    const af = CONTINENTS.find(c => c.name === "Africa");
    const as = CONTINENTS.find(c => c.name === "Asia");
  
    if (sa) buildStorySvg("svg-sa", sa, true);
    if (af) buildStorySvg("svg-af", af, true);
    if (as) buildStorySvg("svg-as", as, false);
  
    // Scroll reveal
    initScrollReveal();
  });