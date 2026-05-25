/* ─────────────────────────────────────────────────────
   main.js  —  WaPo-style interactive world map
   D3 v7 + TopoJSON

   REPLACE sampleData with your real dataset.
   Each entry: { name, lat, lng, value, flag }
   ───────────────────────────────────────────────────── */

   const sampleData = [
    { name: "United States", lat: 38,   lng: -97,  value: 980, flag: "🇺🇸" },
    { name: "Brazil",        lat: -14,  lng: -51,  value: 430, flag: "🇧🇷" },
    { name: "Germany",       lat: 51,   lng: 10,   value: 310, flag: "🇩🇪" },
    { name: "Nigeria",       lat: 9,    lng: 8,    value: 190, flag: "🇳🇬" },
    { name: "India",         lat: 20,   lng: 78,   value: 720, flag: "🇮🇳" },
    { name: "China",         lat: 35,   lng: 105,  value: 850, flag: "🇨🇳" },
    { name: "Australia",     lat: -25,  lng: 133,  value: 220, flag: "🇦🇺" },
    { name: "Russia",        lat: 61,   lng: 105,  value: 510, flag: "🇷🇺" },
    { name: "Argentina",     lat: -34,  lng: -64,  value: 160, flag: "🇦🇷" },
    { name: "Japan",         lat: 36,   lng: 138,  value: 390, flag: "🇯🇵" },
    { name: "South Africa",  lat: -29,  lng: 25,   value: 140, flag: "🇿🇦" },
    { name: "Canada",        lat: 60,   lng: -96,  value: 280, flag: "🇨🇦" },
];

// Metadata in header
document.getElementById("point-count").textContent = sampleData.length;

// ── Dimensions ──────────────────────────────────────
const container = document.getElementById("map-container");
const svg       = d3.select("#map-svg");
const tooltip   = document.getElementById("tooltip");

function getDims() {
    return { w: container.clientWidth, h: container.clientHeight };
}

// ── Projection ──────────────────────────────────────
// Natural Earth — swap to d3.geoMercator() or d3.geoOrthographic() as needed
let { w, h } = getDims();

const projection = d3.geoNaturalEarth1()
    .scale(w / 6.3)
    .translate([w / 2, h / 2]);

const path = d3.geoPath().projection(projection);

// ── Zoom & Pan ──────────────────────────────────────
const zoom = d3.zoom()
    .scaleExtent([1, 8])
    .on("zoom", ({ transform }) => mapGroup.attr("transform", transform));

svg.call(zoom);

const mapGroup = svg.append("g");

// ── Bubble scale ────────────────────────────────────
const maxVal = d3.max(sampleData, d => d.value);
const bubbleR = d3.scaleSqrt().domain([0, maxVal]).range([4, 28]);

// ── Load world TopoJSON ─────────────────────────────
d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(world => {

    mapGroup.append("path")
        .datum({ type: "Sphere" })
        .attr("class", "sphere")
        .attr("d", path);

    mapGroup.append("path")
        .datum(d3.geoGraticule()())
        .attr("class", "graticule")
        .attr("d", path);

    mapGroup.append("g")
        .selectAll("path")
        .data(topojson.feature(world, world.objects.countries).features)
        .join("path")
            .attr("class", "country")
            .attr("d", path)
            .on("click", function() {
                d3.selectAll(".country").classed("active", false);
                d3.select(this).classed("active", true);
            });

    // ── Bubbles ─────────────────────────────────────
    mapGroup.append("g")
        .selectAll("circle")
        .data(sampleData)
        .join("circle")
            .attr("class", "bubble")
            .attr("cx", d => projection([d.lng, d.lat])[0])
            .attr("cy", d => projection([d.lng, d.lat])[1])
            .attr("r",  d => bubbleR(d.value))
            .on("mousemove", function(event, d) {
                const [mx, my] = d3.pointer(event, container);
                tooltip.classList.add("visible");
                tooltip.style.left = (mx + 14) + "px";
                tooltip.style.top  = (my - 42) + "px";
                document.getElementById("tooltip-country").textContent = (d.flag || "") + "  " + d.name;
                document.getElementById("tooltip-value").textContent   = "Value: " + d.value.toLocaleString();
            })
            .on("mouseleave", () => tooltip.classList.remove("visible"))
            .on("click", function(event, d) {
                event.stopPropagation();
                openSidebar(d);
            });

}).catch(err => console.error("Map load failed:", err));

// ── Sidebar detail ──────────────────────────────────
function openSidebar(d) {
    const card = document.getElementById("selectedCard");
    document.getElementById("selectedFlag").textContent   = d.flag || "";
    document.getElementById("selectedName").textContent   = d.name;
    document.getElementById("selectedValue").textContent  = d.value.toLocaleString();
    document.getElementById("selectedCoords").textContent =
        `${Math.abs(d.lat)}°${d.lat >= 0 ? "N" : "S"}, ${Math.abs(d.lng)}°${d.lng >= 0 ? "E" : "W"}`;
    card.style.display = "block";
}

// ── Reset ────────────────────────────────────────────
document.getElementById("resetBtn").addEventListener("click", () => {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
    d3.selectAll(".country").classed("active", false);
    document.getElementById("selectedCard").style.display = "none";
});

svg.on("click", () => d3.selectAll(".country").classed("active", false));

// ── Responsive resize ────────────────────────────────
window.addEventListener("resize", () => {
    const dims = getDims();
    projection.scale(dims.w / 6.3).translate([dims.w / 2, dims.h / 2]);
    mapGroup.selectAll("path").attr("d", path);
    mapGroup.selectAll(".bubble")
        .attr("cx", d => projection([d.lng, d.lat])[0])
        .attr("cy", d => projection([d.lng, d.lat])[1]);
});

/* ─────────────────────────────────────────────────────
   TIPS:

   Change headline text → edit .masthead-title in index.html
   Change article body  → edit .sidebar-lede in index.html
   Change accent color  → edit --red in global.css

   Animate bubbles on load:
       .attr("r", 0)
       .transition().duration(600).delay((_, i) => i * 50)
       .attr("r", d => bubbleR(d.value))

   Color-code by category:
       const color = d3.scaleOrdinal()
           .domain(["Asia","Europe","Americas"])
           .range(["#c0282d","#1a6bab","#2a7a45"]);
       .style("stroke", d => color(d.region))
       .style("fill",   d => color(d.region) + "33")

   Zoom to a point:
       svg.transition().duration(600).call(
           zoom.transform,
           d3.zoomIdentity
               .translate(w/2, h/2)
               .scale(4)
               .translate(-projection([d.lng, d.lat])[0], -projection([d.lng, d.lat])[1])
       );
   ───────────────────────────────────────────────────── */