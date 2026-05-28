/* ─────────────────────────────────────────────────────
   main.js  —  Climate Extreme Weather interactive GLOBE
   D3 v7 + TopoJSON
   ───────────────────────────────────────────────────── */

// ── State ────────────────────────────────────────────
let currentEvent = "heat";
let currentExp   = "historical";
let currentYear  = 1850;
let selectedCode = null;
let allData      = {};
let worldData    = null;
let playInterval = null;

// ── Country name lookup (ISO 3166-1 alpha-2) ─────────
const ISO2_NAMES = {
  AF:"Afghanistan",AO:"Angola",AL:"Albania",AE:"United Arab Emirates",AR:"Argentina",
  AM:"Armenia",AU:"Australia",AT:"Austria",AZ:"Azerbaijan",BI:"Burundi",
  BE:"Belgium",BJ:"Benin",BF:"Burkina Faso",BD:"Bangladesh",BG:"Bulgaria",
  BH:"Bahrain",BS:"Bahamas",BA:"Bosnia and Herzegovina",BY:"Belarus",BZ:"Belize",
  BO:"Bolivia",BR:"Brazil",BN:"Brunei",BT:"Bhutan",BW:"Botswana",
  CF:"Central African Rep.",CG:"Congo",CH:"Switzerland",CI:"Côte d'Ivoire",
  CL:"Chile",CM:"Cameroon",CN:"China",CD:"DR Congo",CO:"Colombia",
  CR:"Costa Rica",CU:"Cuba",CY:"Cyprus",CZ:"Czechia",DE:"Germany",
  DJ:"Djibouti",DK:"Denmark",DO:"Dominican Republic",DZ:"Algeria",
  EC:"Ecuador",EG:"Egypt",ER:"Eritrea",ES:"Spain",ET:"Ethiopia",
  FI:"Finland",FJ:"Fiji",FR:"France",GA:"Gabon",GB:"United Kingdom",
  GE:"Georgia",GH:"Ghana",GN:"Guinea",GQ:"Equatorial Guinea",GR:"Greece",
  GT:"Guatemala",GW:"Guinea-Bissau",GY:"Guyana",HN:"Honduras",HR:"Croatia",
  HT:"Haiti",HU:"Hungary",ID:"Indonesia",IE:"Ireland",IN:"India",IQ:"Iraq",
  IR:"Iran",IS:"Iceland",IL:"Israel",IT:"Italy",JM:"Jamaica",JO:"Jordan",
  JP:"Japan",KE:"Kenya",KG:"Kyrgyzstan",KH:"Cambodia",KP:"North Korea",
  KR:"South Korea",KW:"Kuwait",KZ:"Kazakhstan",LA:"Laos",LB:"Lebanon",
  LK:"Sri Lanka",LR:"Liberia",LS:"Lesotho",LT:"Lithuania",LU:"Luxembourg",
  LV:"Latvia",LY:"Libya",MA:"Morocco",MD:"Moldova",MK:"North Macedonia",
  ML:"Mali",MM:"Myanmar",MN:"Mongolia",MR:"Mauritania",MW:"Malawi",
  MX:"Mexico",MY:"Malaysia",MZ:"Mozambique",NA:"Namibia",NE:"Niger",
  NG:"Nigeria",NI:"Nicaragua",NL:"Netherlands",NO:"Norway",NP:"Nepal",
  NZ:"New Zealand",OM:"Oman",PA:"Panama",PE:"Peru",PG:"Papua New Guinea",
  PH:"Philippines",PK:"Pakistan",PL:"Poland",PR:"Puerto Rico",PT:"Portugal",
  PY:"Paraguay",QA:"Qatar",RO:"Romania",RS:"Serbia",RU:"Russia",RW:"Rwanda",
  SA:"Saudi Arabia",SD:"Sudan",SS:"South Sudan",SN:"Senegal",SL:"Sierra Leone",
  SO:"Somalia",SR:"Suriname",SK:"Slovakia",SI:"Slovenia",SE:"Sweden",
  SY:"Syria",SZ:"Eswatini",TD:"Chad",TG:"Togo",TH:"Thailand",
  TJ:"Tajikistan",TL:"Timor-Leste",TM:"Turkmenistan",TN:"Tunisia",
  TR:"Turkey",TT:"Trinidad and Tobago",TZ:"Tanzania",UA:"Ukraine",
  UG:"Uganda",US:"United States",UY:"Uruguay",UZ:"Uzbekistan",
  VE:"Venezuela",VN:"Vietnam",YE:"Yemen",ZA:"South Africa",ZM:"Zambia",ZW:"Zimbabwe"
};

// ── Numeric ISO → alpha-2 ─────────────────────────────
const NUM_TO_ALPHA2 = {
  4:"AF",8:"AL",10:"AQ",12:"DZ",24:"AO",31:"AZ",32:"AR",36:"AU",40:"AT",48:"BH",
  50:"BD",56:"BE",64:"BT",68:"BO",70:"BA",72:"BW",76:"BR",84:"BZ",90:"SB",96:"BN",
  100:"BG",104:"MM",108:"BI",112:"BY",116:"KH",120:"CM",124:"CA",140:"CF",144:"LK",
  148:"TD",152:"CL",156:"CN",162:"CX",166:"CC",170:"CO",174:"KM",178:"CG",180:"CD",
  188:"CR",191:"HR",192:"CU",196:"CY",203:"CZ",204:"BJ",208:"DK",214:"DO",218:"EC",
  222:"SV",226:"GQ",231:"ET",232:"ER",242:"FJ",246:"FI",250:"FR",260:"TF",262:"DJ",
  266:"GA",276:"DE",288:"GH",296:"KI",300:"GR",316:"GU",320:"GT",324:"GN",328:"GY",
  332:"HT",340:"HN",348:"HU",356:"IN",360:"ID",364:"IR",368:"IQ",372:"IE",376:"IL",
  380:"IT",388:"JM",392:"JP",398:"KZ",400:"JO",404:"KE",408:"KP",410:"KR",414:"KW",
  417:"KG",418:"LA",422:"LB",426:"LS",428:"LV",430:"LR",434:"LY",440:"LT",442:"LU",
  450:"MG",454:"MW",458:"MY",462:"MV",466:"ML",478:"MR",480:"MU",484:"MX",496:"MN",
  498:"MD",504:"MA",508:"MZ",512:"OM",516:"NA",520:"NR",524:"NP",528:"NL",540:"NC",
  548:"VU",554:"NZ",558:"NI",562:"NE",566:"NG",574:"NF",578:"NO",580:"MP",583:"FM",
  584:"MH",585:"PW",586:"PK",591:"PA",598:"PG",600:"PY",604:"PE",608:"PH",616:"PL",
  620:"PT",624:"GW",626:"TL",630:"PR",634:"QA",638:"RE",642:"RO",643:"RU",646:"RW",
  654:"SH",678:"ST",682:"SA",686:"SN",690:"SC",694:"SL",703:"SK",704:"VN",705:"SI",
  706:"SO",710:"ZA",716:"ZW",724:"ES",728:"SS",729:"SD",734:"TN",740:"SR",744:"SJ",
  752:"SE",756:"CH",760:"SY",762:"TJ",764:"TH",768:"TG",776:"TO",780:"TT",784:"AE",
  788:"TN",792:"TR",795:"TM",798:"TV",800:"UG",804:"UA",807:"MK",818:"EG",826:"GB",
  834:"TZ",840:"US",854:"BF",858:"UY",860:"UZ",862:"VE",882:"WS",887:"YE",894:"ZM"
};

// ── Flags ─────────────────────────────────────────────
function getFlag(code) {
    if (!code || code.length !== 2) return "";
    return String.fromCodePoint(...[...code.toUpperCase()].map(c => c.charCodeAt(0) + 127397));
}

// ── Color scale ───────────────────────────────────────
const colorScale = d3.scaleSequential()
    .domain([0, 1])
    .interpolator(d3.interpolateRgb("#f0ebe3", "#c0282d"));

function noDataColor() { return "#d9d4c7"; }

// ── Data loading ──────────────────────────────────────
const DATA_BASE = "./dataframes/";

function dataKey(event, exp) { return `${event}_${exp}`; }

async function loadCSV(event, exp) {
    const key = dataKey(event, exp);
    if (allData[key]) return;
    const filename = `${event}_${exp}_country_year.csv`;
    const url = DATA_BASE + filename;
    console.log(`Loading: ${url}`);
    try {
        const rows = await d3.csv(url, d => ({
            code: d.country_code,
            year: +d.year,
            mean: +d.intensity_mean,
            max:  +d.intensity_max,
            min:  +d.intensity_min,
            n:    +d.n_grid_points,
        }));
        const nested = new Map();
        for (const r of rows) {
            if (!r.code || isNaN(r.year) || isNaN(r.mean)) continue;
            if (!nested.has(r.code)) nested.set(r.code, new Map());
            nested.get(r.code).set(r.year, r);
        }
        allData[key] = nested;
        console.log(`Loaded ${rows.length} rows for ${key}. Countries: ${nested.size}`);
    } catch(e) {
        console.error(`Failed to load ${url}:`, e);
        allData[key] = new Map();
    }
}

// ── Lookup helpers ────────────────────────────────────
function getRow(code, year) {
    const nested = allData[dataKey(currentEvent, currentExp)];
    if (!nested) return null;
    const byYear = nested.get(code);
    if (!byYear) return null;
    return byYear.get(year) || null;
}

function getCountrySeries(code) {
    const nested = allData[dataKey(currentEvent, currentExp)];
    if (!nested) return [];
    const byYear = nested.get(code);
    if (!byYear) return [];
    return Array.from(byYear.values()).sort((a, b) => a.year - b.year);
}

function computeDomain() {
    const nested = allData[dataKey(currentEvent, currentExp)];
    if (!nested) return [0, 1];
    let max = 0;
    for (const byYear of nested.values()) {
        const row = byYear.get(currentYear);
        if (row && row.mean > max) max = row.mean;
    }
    return [0, max || 1];
}

// ── Map setup ─────────────────────────────────────────
const container = document.getElementById("map-container");
const svg       = d3.select("#map-svg");
const tooltip   = document.getElementById("tooltip");

function getDims() {
    return { w: container.clientWidth, h: container.clientHeight };
}
let { w, h } = getDims();

// ── Globe projection ──────────────────────────────────
let baseScale = Math.min(w, h) / 2 - 4;

const projection = d3.geoOrthographic()
    .scale(baseScale)
    .translate([w / 2, h / 2])
    .clipAngle(90)
    .rotate([0, -20]);

const path = d3.geoPath().projection(projection);

function redrawGlobe() {
    svg.select("#globe-clip path").attr("d", path);
    mapGroup.selectAll("path").attr("d", path);
}

// ── d3.drag() for globe rotation ─────────────────────
let dragStartRotation = null;
let dragStartPos      = null;
let isDragging        = false;

const drag = d3.drag()
    .on("start", function(event) {
        isDragging = true;
        dragStartRotation = projection.rotate().slice();
        dragStartPos = [event.x, event.y];
        svg.style("cursor", "grabbing");
        tooltip.classList.remove("visible");
    })
    .on("drag", function(event) {
        if (!dragStartRotation) return;
        const dx = event.x - dragStartPos[0];
        const dy = event.y - dragStartPos[1];
        const sensitivity = 0.4;
        projection.rotate([
            dragStartRotation[0] + dx * sensitivity,
            dragStartRotation[1] - dy * sensitivity
        ]);
        redrawGlobe();
    })
    .on("end", function() {
        isDragging = false;
        dragStartRotation = null;
        dragStartPos = null;
        svg.style("cursor", "grab");
    });

svg.call(drag);
svg.style("cursor", "grab");

// ── Scroll-to-zoom ─────────────────────────────────────
svg.on("wheel", function(event) {
    event.preventDefault();
    const currentScale = projection.scale();
    const minScale = baseScale;
    const maxScale = baseScale * 6;
    const delta    = event.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(minScale, Math.min(maxScale, currentScale * delta));
    projection.scale(newScale);
    redrawGlobe();
}, { passive: false });

// ── Map group ─────────────────────────────────────────
const mapGroup = svg.append("g");

// ── ISO numeric → alpha-2 ─────────────────────────────
const NUM_TO_ALPHA2 = {
  4:"AF",8:"AL",12:"DZ",24:"AO",32:"AR",36:"AU",40:"AT",31:"AZ",48:"BH",50:"BD",
  56:"BE",64:"BT",68:"BO",76:"BR",100:"BG",854:"BF",108:"BI",116:"KH",120:"CM",
  124:"CA",140:"CF",144:"LK",152:"CL",170:"CO",178:"CG",180:"CD",188:"CR",191:"HR",
  192:"CU",196:"CY",203:"CZ",204:"BJ",208:"DK",214:"DO",218:"EC",818:"EG",222:"SV",
  226:"GQ",232:"ER",231:"ET",246:"FI",242:"FJ",266:"GA",276:"DE",288:"GH",300:"GR",
  320:"GT",324:"GN",624:"GW",328:"GY",332:"HT",340:"HN",348:"HU",356:"IN",360:"ID",
  364:"IR",368:"IQ",372:"IE",376:"IL",380:"IT",388:"JM",400:"JO",392:"JP",404:"KE",
  408:"KP",410:"KR",414:"KW",398:"KZ",418:"LA",422:"LB",430:"LR",426:"LS",440:"LT",
  442:"LU",428:"LV",434:"LY",484:"MX",458:"MY",466:"ML",504:"MA",516:"NA",524:"NP",
  528:"NL",554:"NZ",558:"NI",562:"NE",566:"NG",578:"NO",512:"OM",586:"PK",591:"PA",
  598:"PG",600:"PY",604:"PE",608:"PH",616:"PL",620:"PT",630:"PR",634:"QA",642:"RO",
  703:"SK",705:"SI",706:"SO",710:"ZA",724:"ES",729:"SD",740:"SR",752:"SE",
  756:"CH",760:"SY",762:"TJ",764:"TH",768:"TG",780:"TT",788:"TN",792:"TR",800:"UG",
  804:"UA",784:"AE",826:"GB",840:"US",858:"UY",860:"UZ",862:"VE",704:"VN",887:"YE",
  894:"ZM",716:"ZW",646:"RW",686:"SN",694:"SL",807:"MK",498:"MD",508:"MZ",454:"MW",
  148:"TD",156:"CN",643:"RU",72:"BW",84:"BZ",104:"MM",496:"MN"
};

// ── Choropleth update ─────────────────────────────────
function updateChoropleth() {
    const [domMin, domMax] = computeDomain();
    colorScale.domain([domMin, domMax]);
    document.getElementById("rampMax").textContent = domMax.toFixed ? domMax.toFixed(2) : domMax;
    mapGroup.selectAll(".country").each(function(d) {
        const alpha2 = d.properties?.alpha2;
        const row = alpha2 ? getRow(alpha2, currentYear) : null;
        d3.select(this).attr("fill", row ? colorScale(row.mean) : noDataColor());
    });
}

// ── TopoJSON world load ──────────────────────────────
async function initMap() {
    // FIX: correctly read both width and height from container
    const cw = container.clientWidth;
    const ch = container.clientHeight;
    svg.attr("width", cw).attr("height", ch).attr("viewBox", `0 0 ${cw} ${ch}`);

    baseScale = Math.min(cw, ch) / 2 - 4;
    projection.scale(baseScale).translate([cw / 2, ch / 2]);

    const world = await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json");
    worldData = world;

    const features = topojson.feature(world, world.objects.countries).features;
    for (const f of features) {
        const alpha2 = NUM_TO_ALPHA2[+f.id];
        if (!f.properties) f.properties = {};
        f.properties.alpha2 = alpha2 || null;
    }

    svg.append("defs")
        .append("clipPath")
        .attr("id", "globe-clip")
        .append("path")
        .datum({ type: "Sphere" })
        .attr("d", path);

    mapGroup.append("path")
        .datum({ type: "Sphere" })
        .attr("class", "sphere")
        .attr("d", path);

    mapGroup.append("path")
        .datum(d3.geoGraticule()())
        .attr("class", "graticule")
        .attr("d", path)
        .attr("clip-path", "url(#globe-clip)");

    const countryGroup = mapGroup.append("g")
        .attr("clip-path", "url(#globe-clip)");

    countryGroup.selectAll("path")
        .data(features)
        .join("path")
            .attr("class", "country")
            .attr("d", path)
            .attr("fill", noDataColor())
            .on("mousemove", function(event, d) {
                if (isDragging) return;
                const alpha2 = d.properties?.alpha2;
                const row  = alpha2 ? getRow(alpha2, currentYear) : null;
                const name = alpha2 ? (ISO2_NAMES[alpha2] || alpha2) : "Unknown";

                const tx = event.clientX + 14;
                const ty = event.clientY - 60;
                const ttW = 160;
                const left = tx + ttW > window.innerWidth ? event.clientX - ttW - 8 : tx;

                tooltip.classList.add("visible");
                tooltip.style.left = left + "px";
                tooltip.style.top  = Math.max(8, ty) + "px";

                document.getElementById("tooltip-country").textContent =
                    (alpha2 ? getFlag(alpha2) + "  " : "") + name;
                document.getElementById("tooltip-value").textContent =
                    row ? `Mean intensity: ${row.mean.toFixed(4)}` : "No data";
                document.getElementById("tooltip-extra").textContent =
                    row ? `Grid points: ${row.n}` : "";
            })
            .on("mouseleave", () => {
                if (!isDragging) tooltip.classList.remove("visible");
            })
            .on("click", function(event, d) {
                if (isDragging) return;
                event.stopPropagation();
                const alpha2 = d.properties?.alpha2;
                if (!alpha2) return;
                d3.selectAll(".country").classed("active", false);
                d3.select(this).classed("active", true);
                pinCountry(alpha2);
            });

    svg.on("click.deselect", () => {
        if (!isDragging) d3.selectAll(".country").classed("active", false);
    });

    await loadCSV(currentEvent, currentExp);
    updateChoropleth();

    // ── Debug: check code matching ──
    const nested = allData[dataKey(currentEvent, currentExp)];
    const csvCodes = new Set(nested.keys());
    const mapCodes = new Set();
    mapGroup.selectAll(".country").each(function(d) {
        if (d.properties?.alpha2) mapCodes.add(d.properties.alpha2);
    });
    const matched   = [...csvCodes].filter(c => mapCodes.has(c));
    const unmatched = [...csvCodes].filter(c => !mapCodes.has(c));
    console.log(`CSV codes: ${csvCodes.size} | Map codes: ${mapCodes.size} | Matched: ${matched.length}`);
    console.log("Unmatched CSV codes (in CSV but not on map):", unmatched.join(", "));
    console.log("Map codes not in CSV:", [...mapCodes].filter(c => !csvCodes.has(c)).join(", "));
}

// ── Pin country ───────────────────────────────────────
function pinCountry(alpha2) {
    selectedCode = alpha2;
    const name = ISO2_NAMES[alpha2] || alpha2;
    const row  = getRow(alpha2, currentYear);
    document.getElementById("selectedFlag").textContent  = getFlag(alpha2);
    document.getElementById("selectedName").textContent  = name;
    document.getElementById("selectedValue").textContent = row ? row.mean.toFixed(4) : "N/A";
    document.getElementById("selectedYear").textContent  = currentYear;
    document.getElementById("selectedCode").textContent  = alpha2;
    document.getElementById("selectedCard").style.display = "block";
    updateChart(alpha2);
}

// ── Historical chart ──────────────────────────────────
function updateChart(alpha2) {
    const name     = ISO2_NAMES[alpha2] || alpha2;
    const series   = getCountrySeries(alpha2);
    const panel    = document.getElementById("chartPanel");
    const chartSvg = d3.select("#chart-svg");
    chartSvg.selectAll("*").remove();
    document.getElementById("chartTitle").textContent =
        `${getFlag(alpha2)} ${name} — ${currentEvent} intensity (${currentExp})`;
    panel.classList.add("visible");

    if (!series.length) {
        chartSvg.append("text").attr("x", 20).attr("y", 60)
            .attr("font-family", "var(--font-ui)").attr("font-size", 12)
            .attr("fill", "var(--ink-muted)")
            .text("No data available for this country / event combination.");
        return;
    }

    const svgEl  = document.getElementById("chart-svg");
    const W      = svgEl.clientWidth  || 800;
    const H      = svgEl.clientHeight || 130;
    const margin = { top: 10, right: 20, bottom: 28, left: 48 };
    const iW     = W - margin.left - margin.right;
    const iH     = H - margin.top  - margin.bottom;

    const g = chartSvg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const xScale = d3.scaleLinear().domain([1850, 2014]).range([0, iW]);
    const yMax   = d3.max(series, d => d.mean) * 1.05 || 1;
    const yScale = d3.scaleLinear().domain([0, yMax]).range([iH, 0]);

    const area = d3.area().x(d => xScale(d.year)).y0(iH).y1(d => yScale(d.mean)).curve(d3.curveMonotoneX);
    const line = d3.line().x(d => xScale(d.year)).y(d => yScale(d.mean)).curve(d3.curveMonotoneX);

    g.append("path").datum(series).attr("class", "chart-area").attr("d", area);
    g.append("path").datum(series).attr("class", "chart-line").attr("d", line);

    g.append("line").attr("class", "chart-year-line")
        .attr("x1", xScale(currentYear)).attr("x2", xScale(currentYear))
        .attr("y1", 0).attr("y2", iH);

    g.append("text")
        .attr("x", Math.min(xScale(currentYear) + 3, iW - 30)).attr("y", 10)
        .attr("font-family", "var(--font-ui)").attr("font-size", 9)
        .attr("fill", "var(--ink-muted)").text(currentYear);

    g.append("g").attr("class", "chart-axis").attr("transform", `translate(0,${iH})`)
        .call(d3.axisBottom(xScale).ticks(8).tickFormat(d3.format("d")));
    g.append("g").attr("class", "chart-axis")
        .call(d3.axisLeft(yScale).ticks(4).tickFormat(d3.format(".2f")));

    g.append("text").attr("transform", "rotate(-90)").attr("x", -iH / 2).attr("y", -40)
        .attr("text-anchor", "middle").attr("font-family", "var(--font-ui)")
        .attr("font-size", 9).attr("fill", "var(--ink-muted)").text("Intensity (mean)");
}

// ── Year slider ───────────────────────────────────────
const yearSlider  = document.getElementById("yearSlider");
const yearDisplay = document.getElementById("yearDisplay");

yearSlider.addEventListener("input", async () => {
    currentYear = +yearSlider.value;
    yearDisplay.textContent = currentYear;
    await loadCSV(currentEvent, currentExp);
    updateChoropleth();
    if (selectedCode) {
        const row = getRow(selectedCode, currentYear);
        document.getElementById("selectedValue").textContent = row ? row.mean.toFixed(4) : "N/A";
        document.getElementById("selectedYear").textContent  = currentYear;
        if (document.getElementById("chartPanel").classList.contains("visible")) updateChart(selectedCode);
    }
});

// ── Play animation ────────────────────────────────────
const playBtn = document.getElementById("playBtn");
playBtn.addEventListener("click", () => {
    if (playInterval) {
        clearInterval(playInterval); playInterval = null;
        playBtn.textContent = "▶ Play"; playBtn.classList.remove("playing");
        return;
    }
    playBtn.textContent = "⏹ Stop"; playBtn.classList.add("playing");
    if (currentYear >= 2014) { currentYear = 1850; yearSlider.value = 1850; }

    playInterval = setInterval(async () => {
        currentYear++; yearSlider.value = currentYear; yearDisplay.textContent = currentYear;
        await loadCSV(currentEvent, currentExp);
        updateChoropleth();
        if (selectedCode) {
            const row = getRow(selectedCode, currentYear);
            document.getElementById("selectedValue").textContent = row ? row.mean.toFixed(4) : "N/A";
            document.getElementById("selectedYear").textContent  = currentYear;
        }
        if (currentYear >= 2014) {
            clearInterval(playInterval); playInterval = null;
            playBtn.textContent = "▶ Play"; playBtn.classList.remove("playing");
        }
    }, 120);
});

// ── Event tabs ────────────────────────────────────────
document.querySelectorAll(".event-tab").forEach(btn => {
    btn.addEventListener("click", async () => {
        document.querySelectorAll(".event-tab").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentEvent = btn.dataset.event;
        await loadCSV(currentEvent, currentExp);
        updateChoropleth();
        if (selectedCode) updateChart(selectedCode);
    });
});

// ── Experiment toggle ─────────────────────────────────
document.querySelectorAll(".exp-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
        document.querySelectorAll(".exp-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentExp = btn.dataset.exp;
        await loadCSV(currentEvent, currentExp);
        updateChoropleth();
        if (selectedCode) updateChart(selectedCode);
    });
});

// ── Reset ─────────────────────────────────────────────
document.getElementById("resetBtn").addEventListener("click", () => {
    projection.rotate([0, -20]);
    projection.scale(baseScale);
    redrawGlobe();
    d3.selectAll(".country").classed("active", false);
    document.getElementById("selectedCard").style.display = "none";
    selectedCode = null;
});

// ── Chart close ───────────────────────────────────────
document.getElementById("chartClose").addEventListener("click", () => {
    document.getElementById("chartPanel").classList.remove("visible");
    d3.selectAll(".country").classed("active", false);
    selectedCode = null;
    document.getElementById("selectedCard").style.display = "none";
});

// ── Resize ────────────────────────────────────────────
window.addEventListener("resize", () => {
    const cw = container.clientWidth;
    const ch = container.clientHeight;
    baseScale = Math.min(cw, ch) / 2 - 4;
    projection.scale(baseScale).translate([cw / 2, ch / 2]);
    svg.attr("width", cw).attr("height", ch).attr("viewBox", `0 0 ${cw} ${ch}`);
    redrawGlobe();
    if (selectedCode && document.getElementById("chartPanel").classList.contains("visible")) {
        updateChart(selectedCode);
    }
});

// ── Count display ─────────────────────────────────────
document.getElementById("point-count").textContent = Object.keys(ISO2_NAMES).length;

// ── Boot ──────────────────────────────────────────────
let initialized = false;
const ro = new ResizeObserver(entries => {
    const entry = entries[0];
    const { width, height } = entry.contentRect;
    if (width === 0 || height === 0) return;

    if (!initialized) {
        initialized = true;
        baseScale = Math.min(width, height) / 2 - 4;
        projection.scale(baseScale).translate([width / 2, height / 2]);
        ro.disconnect();
        initMap();
    }
});
ro.observe(container);
