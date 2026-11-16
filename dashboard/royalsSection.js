import { attachTooltip, clearNode, formatInteger, formatSigned, formatText, htmlElement, linearScale, roundTicks, svgElement } from "./svgToolkit.js";

const PLOT = { width: 520, rowHeight: 34, left: 150, right: 44, top: 8, bottom: 30, barHeight: 12, groupGap: 14 };
const PHASE_NAMES = { powerplay: "powerplay", middle: "middle overs", death: "death overs" };
const PHASE_ORDER = ["powerplay", "middle", "death"];
const DISCIPLINES = ["batting", "bowling"];
const BAR_RADIUS = 4;
const LABEL_GAP = 6;

function orderedRecord(record) {
  return DISCIPLINES.flatMap((discipline) => PHASE_ORDER.map((phase) =>
    record.find((row) => row.discipline === discipline && row.phase === phase)));
}

function gapBarPath(zero, end, top, height) {
  const direction = end >= zero ? 1 : -1;
  const length = Math.max(Math.abs(end - zero), 1);
  const radius = Math.min(BAR_RADIUS, length);
  const straight = (length - radius) * direction;
  const sweep = direction === 1 ? 1 : 0;
  return `M${zero},${top} h${straight} a${radius},${radius} 0 0 ${sweep} ${radius * direction},${radius} v${height - 2 * radius} a${radius},${radius} 0 0 ${sweep} ${-radius * direction},${radius} h${-straight} z`;
}

/** One neutral series: the sign is carried by which side of zero the bar sits, not by colour. */
export function renderRoyalsPlot(container, record) {
  const rows = orderedRecord(record);
  const extent = Math.max(...rows.map((row) => Math.abs(row.gap)));
  const scale = linearScale([-extent, extent], [PLOT.left + PLOT.right, PLOT.width - PLOT.right]);
  const height = PLOT.top + rows.length * PLOT.rowHeight + PLOT.groupGap + PLOT.bottom;
  const plotBottom = height - PLOT.bottom;
  const svg = svgElement("svg", { viewBox: `0 0 ${PLOT.width} ${height}`, role: "img", "aria-label": "Royals impact per 100 pressure balls minus the other teams, by discipline and phase" });
  for (const tick of roundTicks(-extent, extent, 4)) {
    svg.append(svgElement("line", { class: tick === 0 ? "baseline" : "gridline", x1: scale(tick), x2: scale(tick), y1: PLOT.top, y2: plotBottom }));
    svg.append(svgElement("text", { class: "tick", x: scale(tick), y: plotBottom + 15, "text-anchor": "middle" }, formatSigned(tick, 0)));
  }
  svg.append(svgElement("text", { class: "axisTitle", x: PLOT.width - PLOT.right, y: height - 2, "text-anchor": "end" }, "← behind the other teams   ahead →"));
  rows.forEach((row, position) => {
    const groupOffset = row.discipline === DISCIPLINES[1] ? PLOT.groupGap : 0;
    const top = PLOT.top + position * PLOT.rowHeight + groupOffset + (PLOT.rowHeight - PLOT.barHeight) / 2;
    const end = scale(row.gap);
    const label = svgElement("text", { x: 0, y: top + PLOT.barHeight - 1.5, "font-size": 12.5 }, `${row.discipline === "batting" ? "Batting" : "Bowling"}, ${PHASE_NAMES[row.phase]}`);
    label.style.fill = "var(--ink)";
    const bar = svgElement("path", { d: gapBarPath(scale(0), end, top, PLOT.barHeight), fill: "var(--ink)", tabindex: 0 });
    attachTooltip(bar, () => ({ title: `${label.textContent}`, rows: [["Royals", formatSigned(row.royals)], ["Other teams", formatSigned(row.others)],
      ["Gap", formatSigned(row.gap)], ["Royals pressure balls", formatInteger(row.royalsBalls)]] }));
    const valueLabel = svgElement("text", { x: row.gap >= 0 ? end + LABEL_GAP : end - LABEL_GAP, y: top + PLOT.barHeight - 1.5, "font-size": 12, "text-anchor": row.gap >= 0 ? "start" : "end" }, formatSigned(row.gap));
    valueLabel.style.fill = "var(--ink)";
    svg.append(label, bar, valueLabel);
  });
  clearNode(container).append(svg);
}

function rankText(rank, eligibleCount) {
  return rank === null ? formatText(null) : `${rank} of ${eligibleCount}`;
}

export function renderSquadTable(table, note, royals, eligibleCounts) {
  const head = htmlElement("thead");
  const headRow = htmlElement("tr");
  for (const label of ["Player", "Batting rank", "Batting pressure impact", "Bowling rank", "Bowling pressure impact"]) {
    headRow.append(htmlElement("th", "", label));
  }
  head.append(headRow);
  const body = htmlElement("tbody");
  for (const player of royals.squad) {
    const row = htmlElement("tr");
    row.append(htmlElement("td", "text", player.playerName),
      htmlElement("td", "", rankText(player.batting_rank, eligibleCounts.batter)),
      htmlElement("td", "", formatSigned(player.batting_rawPressureImpact)),
      htmlElement("td", "", rankText(player.bowling_rank, eligibleCounts.bowler)),
      htmlElement("td", "", formatSigned(player.bowling_rawPressureImpact)));
    body.append(row);
  }
  clearNode(table).append(head, body);
  note.textContent = `The other ${royals.unratedSquadMembers} squad members have too few pressure balls in the data to rate.`;
}
