import { clearNode, formatDecimal, formatInteger, formatPercent, formatSigned, formatText, htmlElement, linearScale, svgElement } from "./svgToolkit.js";

const CHART_WIDTH = 360;
const CHART_HEIGHT = 46;
const CHART_PADDING = 14;
const MARK_ROW = 20;
const MARK_SIZE = 5.5;
const ANCHOR_MARGIN = 50;
const PHASES = [["powerplayShare", "Powerplay"], ["middleShare", "Middle"], ["deathShare", "Death"]];
const NO_TEAM_TEXT = "not in the latest IPL squads";

function statusLabel(player, eligibleCount, listSize) {
  if (player.finalRank !== null && player.finalRank <= listSize) {
    return { text: `Listed: No. ${player.finalRank}`, isListed: true };
  }
  if (!player.provenUnderPressure) {
    return { text: "Not listed: pressure record below average", isListed: false };
  }
  if (!player.passesDipGate) {
    return { text: "Not listed: dips below usual level", isListed: false };
  }
  return { text: `Rated ${player.rank} of ${eligibleCount}`, isListed: false };
}

function figure(label, value, detail = "") {
  const block = htmlElement("div");
  const valueNode = htmlElement("span", "figureValue", value);
  if (detail) {
    valueNode.append(" ", htmlElement("small", "", detail));
  }
  block.append(htmlElement("span", "figureLabel", label), valueNode);
  return block;
}

function levelChart(player) {
  const values = [0, player.rawBaselineImpact, player.rawPressureImpact, player.rating];
  const scale = linearScale([Math.min(...values), Math.max(...values)], [CHART_PADDING, CHART_WIDTH - CHART_PADDING]);
  const svg = svgElement("svg", { viewBox: `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`, role: "img",
    "aria-label": `Usual level ${formatSigned(player.rawBaselineImpact)}, pressure record ${formatSigned(player.rawPressureImpact)}, rating ${formatDecimal(player.rating)} runs per 100 balls` });
  svg.append(svgElement("line", { class: "gridline", x1: CHART_PADDING, x2: CHART_WIDTH - CHART_PADDING, y1: MARK_ROW, y2: MARK_ROW }));
  svg.append(svgElement("line", { class: "baseline", x1: scale(0), x2: scale(0), y1: 6, y2: MARK_ROW + 14 }));
  const zeroAnchor = scale(0) < ANCHOR_MARGIN ? "start" : scale(0) > CHART_WIDTH - ANCHOR_MARGIN ? "end" : "middle";
  svg.append(svgElement("text", { class: "tick", x: scale(0), y: CHART_HEIGHT - 2, "text-anchor": zeroAnchor }, "average player"));
  svg.append(svgElement("line", { x1: scale(player.rawBaselineImpact), x2: scale(player.rawPressureImpact), y1: MARK_ROW, y2: MARK_ROW, stroke: "var(--axis)", "stroke-width": 3 }));
  svg.append(svgElement("circle", { cx: scale(player.rawBaselineImpact), cy: MARK_ROW, r: MARK_SIZE, fill: "var(--usual)", stroke: "var(--plane)", "stroke-width": 2 }));
  const pressureX = scale(player.rawPressureImpact);
  svg.append(svgElement("rect", { x: pressureX - MARK_SIZE, y: MARK_ROW - MARK_SIZE, width: MARK_SIZE * 2, height: MARK_SIZE * 2, fill: "var(--pressure)", stroke: "var(--plane)", "stroke-width": 2 }));
  const ratingX = scale(player.rating);
  svg.append(svgElement("rect", { x: ratingX - MARK_SIZE, y: MARK_ROW - MARK_SIZE, width: MARK_SIZE * 2, height: MARK_SIZE * 2, fill: "var(--ink)", stroke: "var(--plane)", "stroke-width": 2, transform: `rotate(45 ${ratingX} ${MARK_ROW})` }));
  return svg;
}

function levelLegend(player) {
  const legend = htmlElement("div", "phaseLegend levelLegend");
  const entries = [["keyUsual", "Usual level", formatSigned(player.rawBaselineImpact)],
    ["keyPressure", "Pressure balls", formatSigned(player.rawPressureImpact)],
    ["keyRating", "Rating", formatDecimal(player.rating)]];
  for (const [keyClass, label, value] of entries) {
    const entry = htmlElement("span");
    entry.append(htmlElement("span", `key ${keyClass}`), `${label} `, htmlElement("b", "", value));
    legend.append(entry);
  }
  return legend;
}

function phaseSplit(player) {
  const bar = htmlElement("div", "phaseBar");
  const legend = htmlElement("div", "phaseLegend");
  for (const [key, label] of PHASES) {
    const share = player[key] ?? 0;
    const segment = htmlElement("span");
    segment.style.flex = `${share} 0 0`;
    bar.append(segment);
    const entry = htmlElement("span", "", `${label} `);
    entry.append(htmlElement("b", "", formatPercent(share)));
    legend.append(entry);
  }
  bar.setAttribute("role", "img");
  bar.setAttribute("aria-label", "Share of pressure balls by phase");
  return [bar, legend];
}

function statRows(player, role) {
  const shared = [["Pressure outings above par", formatPercent(player.rawOutingRate)],
    ["Chance pressure is below usual", formatPercent(player.dipProbability)], ["Last match in data", formatText(player.lastMatch)]];
  if (role === "batter") {
    return [["Pressure balls faced", formatInteger(player.ballsPressure)], ["Pressure strike rate", formatDecimal(player.strikeRatePressure, 0)],
      ["Pressure average", formatDecimal(player.averagePressure)], ["Usual strike rate", formatDecimal(player.strikeRateBaseline, 0)],
      ["Strike rate against pace", formatDecimal(player.strikeRateVsPace, 0)], ["Strike rate against spin", formatDecimal(player.strikeRateVsSpin, 0)],
      ["Usually bats at", formatDecimal(player.typicalPosition, 0)], ...shared];
  }
  return [["Pressure balls bowled", formatInteger(player.ballsPressure)], ["Pressure economy", formatDecimal(player.economyPressure, 2)],
    ["Pressure wickets", formatInteger(player.wicketsPressure)], ["Usual economy", formatDecimal(player.economyBaseline, 2)],
    ["Powerplay economy", formatDecimal(player.powerplayEconomy, 2)], ["Middle-overs economy", formatDecimal(player.middleEconomy, 2)],
    ["Death economy", formatDecimal(player.deathEconomy, 2)], ...shared];
}

function statGrid(rows) {
  const grid = htmlElement("dl", "statGrid");
  for (const [label, value] of rows) {
    const row = htmlElement("div");
    row.append(htmlElement("dt", "", label), htmlElement("dd", "", value));
    grid.append(row);
  }
  return grid;
}

export function renderPlayerCard(container, player, role, eligibleCount, listSize) {
  clearNode(container);
  const status = statusLabel(player, eligibleCount, listSize);
  const descriptor = role === "bowler" ? formatText(player.bowlingType) : "Batter";
  const figures = htmlElement("div", "figureRow");
  figures.append(figure("Rating", formatDecimal(player.rating), `± ${formatDecimal(player.posteriorSd)}`),
    figure("Top-ten chance", formatPercent(player.topListProbability)),
    figure("Rank range", `${formatDecimal(player.rankLow, 0)}–${formatDecimal(player.rankHigh, 0)}`));
  container.append(
    htmlElement("h4", "", player.playerName),
    htmlElement("div", "cardMeta", `${descriptor} · ${player.latestIplTeam ?? NO_TEAM_TEXT}`),
    htmlElement("span", status.isListed ? "status isListed" : "status", status.text),
    figures,
    htmlElement("div", "cardHeading", "Runs per 100 balls against an average player"),
    levelChart(player), levelLegend(player),
    htmlElement("div", "cardHeading", "Where the pressure balls come"),
    ...phaseSplit(player),
    htmlElement("div", "cardHeading", "Record"),
    statGrid(statRows(player, role)),
  );
}
