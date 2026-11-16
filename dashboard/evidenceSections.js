import { attachTooltip, clearNode, cssVariable, formatDecimal, formatInteger, formatPercent, htmlElement, linearScale, roundTicks, svgElement } from "./svgToolkit.js";

const CELL_GAP = 2;
const HEATMAP = { width: 520, height: 330, left: 74, top: 6, bottom: 40 };
const WHITE_TEXT_LUMINANCE = 0.179;
const LINEAR_THRESHOLD = 0.04045;
const REPEAT = { width: 520, rowHeight: 50, left: 150, top: 26, panelGap: 26, barHeight: 12, right: 34 };
const REPEAT_MEASURES = [["expectedPressureImpact", "Blended rating"], ["rawBaselineImpact", "Usual-level record"],
  ["rawPressureImpact", "Pressure record alone"], ["rawLift", "Lift: pressure minus usual"]];
const INTERVAL = { width: 520, rowHeight: 22, left: 150, top: 8, bottom: 30, right: 12, shown: 15 };
const COMPARISON_ROWS = [["meanSwing", "Result swing per ball", (value) => `${formatDecimal(value * 100, 1)} pts`, true],
  ["runsPerBall", "Runs per ball", (value) => formatDecimal(value, 2), false],
  ["wicketRate", "Wicket", (value) => formatPercent(value, 1), false],
  ["dotRate", "Dot ball", (value) => formatPercent(value, 1), false],
  ["boundaryRate", "Boundary", (value) => formatPercent(value, 1), false]];

function parseColour(hex) {
  return [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16));
}

function mixColour(low, high, share) {
  return low.map((channel, position) => Math.round(channel + (high[position] - channel) * share));
}

/** WCAG relative luminance; below WHITE_TEXT_LUMINANCE white text has the better contrast, above it near-black does. */
function luminance(colour) {
  const [red, green, blue] = colour.map((channel) => {
    const share = channel / 255;
    return share <= LINEAR_THRESHOLD ? share / 12.92 : ((share + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

export function renderHeatmap(container, heatmap) {
  const low = parseColour(cssVariable("--rampLow"));
  const high = parseColour(cssVariable("--rampHigh"));
  const cellWidth = (HEATMAP.width - HEATMAP.left) / heatmap.ballLabels.length;
  const cellHeight = (HEATMAP.height - HEATMAP.top - HEATMAP.bottom) / heatmap.rateLabels.length;
  const svg = svgElement("svg", { viewBox: `0 0 ${HEATMAP.width} ${HEATMAP.height}`, role: "img",
    "aria-label": "Share of chase balls classed as pressure, by required runs per over and balls left" });
  heatmap.rateLabels.forEach((rateLabel, row) => {
    const top = HEATMAP.top + row * cellHeight;
    svg.append(svgElement("text", { class: "tick", x: HEATMAP.left - 10, y: top + cellHeight / 2 + 4, "text-anchor": "end" }, rateLabel));
    heatmap.ballLabels.forEach((ballLabel, column) => {
      const share = heatmap.pressureShare[row][column];
      const colour = mixColour(low, high, share);
      const left = HEATMAP.left + column * cellWidth;
      const cell = svgElement("rect", { x: left + CELL_GAP / 2, y: top + CELL_GAP / 2, width: cellWidth - CELL_GAP,
        height: cellHeight - CELL_GAP, fill: `rgb(${colour.join(",")})`, tabindex: 0 });
      attachTooltip(cell, () => ({ title: `${rateLabel} an over, ${ballLabel} balls left`,
        rows: [["Pressure balls", formatPercent(share)], ["Chase balls in this cell", formatInteger(heatmap.balls[row][column])]] }));
      const label = svgElement("text", { x: left + cellWidth / 2, y: top + cellHeight / 2 + 4, "text-anchor": "middle", "font-size": 12, "font-weight": 500, "pointer-events": "none" }, formatPercent(share));
      label.style.fill = luminance(colour) < WHITE_TEXT_LUMINANCE ? "#ffffff" : "#0b0b0b";
      svg.append(cell, label);
    });
  });
  heatmap.ballLabels.forEach((ballLabel, column) => {
    svg.append(svgElement("text", { class: "tick", x: HEATMAP.left + (column + 0.5) * cellWidth, y: HEATMAP.height - HEATMAP.bottom + 16, "text-anchor": "middle" }, ballLabel));
  });
  svg.append(svgElement("text", { class: "axisTitle", x: HEATMAP.left, y: HEATMAP.height - 4 }, "Balls left in the chase →"));
  svg.append(svgElement("text", { class: "axisTitle", x: 12, y: HEATMAP.top, transform: `rotate(-90 12 ${HEATMAP.top})`, "text-anchor": "end" }, "Required runs per over →"));
  clearNode(container).append(svg);
}

export function renderComparison(container, comparison) {
  clearNode(container);
  const head = htmlElement("div", "head");
  head.append(htmlElement("dt", "", "Per legal ball"), htmlElement("dd", "", "Pressure"), htmlElement("dd", "", "Ordinary"));
  container.append(head);
  for (const [key, label, format, isLead] of COMPARISON_ROWS) {
    const row = htmlElement("div", isLead ? "lead" : "");
    row.append(htmlElement("dt", "", label), htmlElement("dd", "", format(comparison.pressure[key])), htmlElement("dd", "", format(comparison.ordinary[key])));
    container.append(row);
  }
}

/** Two small multiples on one scale, one neutral series each: the comparison is between rows, not colours. */
export function renderRepeatPlot(container, roles) {
  const panels = [["batter", "Batters"], ["bowler", "Bowlers"]];
  const values = panels.flatMap(([role]) => REPEAT_MEASURES.map(([key]) => roles[role].splitHalf[key].halfCorrelation));
  const panelWidth = (REPEAT.width - REPEAT.left - REPEAT.panelGap) / panels.length;
  const height = REPEAT.top + REPEAT_MEASURES.length * REPEAT.rowHeight + 8;
  const svg = svgElement("svg", { viewBox: `0 0 ${REPEAT.width} ${height}`, role: "img", "aria-label": "Split-half correlation of each measure for batters and bowlers" });
  REPEAT_MEASURES.forEach(([, label], row) => {
    const text = svgElement("text", { x: 0, y: REPEAT.top + row * REPEAT.rowHeight + REPEAT.rowHeight / 2 + 4, "font-size": 12.5 }, label);
    text.style.fill = "var(--ink)";
    svg.append(text);
  });
  panels.forEach(([role, title], panel) => {
    const left = REPEAT.left + panel * (panelWidth + REPEAT.panelGap);
    const scale = linearScale([0, Math.max(...values)], [left, left + panelWidth - REPEAT.right]);
    svg.append(svgElement("text", { x: left, y: 12, "font-size": 12, "font-weight": 600 }, title));
    svg.append(svgElement("line", { class: "baseline", x1: left, x2: left, y1: REPEAT.top, y2: height - 8 }));
    REPEAT_MEASURES.forEach(([key, label], row) => {
      const value = roles[role].splitHalf[key].halfCorrelation;
      const top = REPEAT.top + row * REPEAT.rowHeight + (REPEAT.rowHeight - REPEAT.barHeight) / 2;
      const width = Math.max(scale(Math.max(value, 0)) - left, 1);
      const bar = svgElement("path", { d: roundedBar(left, top, width, REPEAT.barHeight), fill: "var(--ink)", tabindex: 0 });
      attachTooltip(bar, () => ({ title: `${title}: ${label}`, rows: [["Correlation between halves", formatDecimal(value, 2)]] }));
      const valueLabel = svgElement("text", { x: left + width + 6, y: top + REPEAT.barHeight - 1.5, "font-size": 12 }, formatDecimal(value, 2));
      valueLabel.style.fill = "var(--ink)";
      svg.append(bar, valueLabel);
    });
  });
  clearNode(container).append(svg);
}

function roundedBar(left, top, width, height) {
  const radius = Math.min(4, width);
  return `M${left},${top} h${width - radius} a${radius},${radius} 0 0 1 ${radius},${radius} v${height - 2 * radius} a${radius},${radius} 0 0 1 -${radius},${radius} h-${width - radius} z`;
}

export function renderIntervalPlot(container, players, listSize) {
  const shown = [...players].sort((first, second) => first.rank - second.rank).slice(0, INTERVAL.shown);
  const widest = Math.max(...shown.map((player) => player.rankHigh));
  const height = INTERVAL.top + shown.length * INTERVAL.rowHeight + INTERVAL.bottom;
  const scale = linearScale([1, widest], [INTERVAL.left, INTERVAL.width - INTERVAL.right]);
  const svg = svgElement("svg", { viewBox: `0 0 ${INTERVAL.width} ${height}`, role: "img", "aria-label": "Rank intervals under resampling for the fifteen highest-rated players" });
  const plotBottom = height - INTERVAL.bottom;
  for (const tick of roundTicks(0, widest, 6).filter((value) => value > 0)) {
    svg.append(svgElement("line", { class: "gridline", x1: scale(tick), x2: scale(tick), y1: INTERVAL.top, y2: plotBottom }));
    svg.append(svgElement("text", { class: "tick", x: scale(tick), y: plotBottom + 15, "text-anchor": "middle" }, String(tick)));
  }
  svg.append(svgElement("line", { x1: scale(listSize + 0.5), x2: scale(listSize + 0.5), y1: INTERVAL.top, y2: plotBottom, stroke: "var(--accent)", "stroke-width": 1 }));
  svg.append(svgElement("text", { class: "axisTitle", x: INTERVAL.left, y: height - 2 }, "Rank among eligible players →"));
  shown.forEach((player, row) => {
    const middle = INTERVAL.top + row * INTERVAL.rowHeight + INTERVAL.rowHeight / 2;
    const listed = player.finalRank !== null && player.finalRank <= listSize;
    const colour = listed ? "var(--ink)" : "var(--inkMuted)";
    const name = svgElement("text", { x: INTERVAL.left - 12, y: middle + 4, "text-anchor": "end", "font-size": 12 }, player.playerName);
    name.style.fill = listed ? "var(--ink)" : "var(--inkSecondary)";
    const range = svgElement("line", { x1: scale(player.rankLow), x2: scale(player.rankHigh), y1: middle, y2: middle, stroke: colour, "stroke-width": 2, "stroke-linecap": "round" });
    const dot = svgElement("circle", { cx: scale(player.rankMedian), cy: middle, r: 4.5, fill: listed ? colour : "var(--surface)", stroke: listed ? "var(--surface)" : colour, "stroke-width": listed ? 2 : 1.5 });
    const hit = svgElement("rect", { class: "hit", x: 0, y: middle - INTERVAL.rowHeight / 2, width: INTERVAL.width, height: INTERVAL.rowHeight, tabindex: 0 });
    attachTooltip(hit, () => ({ title: player.playerName, rows: [["Median rank", formatDecimal(player.rankMedian, 0)],
      ["5th to 95th percentile", `${formatDecimal(player.rankLow, 0)} to ${formatDecimal(player.rankHigh, 0)}`],
      ["Chance of a top-ten place", formatPercent(player.topListProbability)]] }));
    svg.append(name, range, dot, hit);
  });
  clearNode(container).append(svg);
}

export function renderSensitivityTable(table, roles) {
  const head = htmlElement("thead");
  const headRow = htmlElement("tr");
  for (const label of ["Assumption changed", "Batters: top ten kept", "Rank correlation", "Bowlers: top ten kept", "Rank correlation"]) {
    headRow.append(htmlElement("th", "", label));
  }
  head.append(headRow);
  const body = htmlElement("tbody");
  roles.batter.sensitivity.forEach((batterRow, position) => {
    const bowlerRow = roles.bowler.sensitivity[position];
    const row = htmlElement("tr");
    row.append(htmlElement("td", "text", batterRow.variant));
    for (const variant of [batterRow, bowlerRow]) {
      row.append(htmlElement("td", "", `${variant.topListOverlap} of ${variant.headlineTopStillEligible}`),
        htmlElement("td", "", formatDecimal(variant.rankCorrelation, 2)));
    }
    body.append(row);
  });
  clearNode(table).append(head, body);
}
