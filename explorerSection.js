import { clearNode, formatDecimal, formatInteger, formatPercent, formatSigned, formatText, hideTooltip, htmlElement, linearScale, roundTicks, showTooltipAt, svgElement } from "./svgToolkit.js";

const PLOT_WIDTH = 640;
const PLOT_HEIGHT = 440;
const MARGIN = { top: 14, right: 18, bottom: 44, left: 52 };
const DOMAIN_PADDING = 6;
const TICK_COUNT = 6;
const DOT_RADIUS = 4.5;
const SELECTED_RADIUS = 6.5;
const SNAP_DISTANCE = 30;
const LABELLED_RANKS = 3;
const LABEL_OFFSET = 9;
const FLIPPED_LABEL_DROP = 19;
const LABEL_FLIP_SHARE = 0.7;
const SHARED_COLUMNS = [
  { key: "rank", label: "Rated", format: formatInteger },
  { key: "playerName", label: "Player", format: formatText, isText: true },
  { key: "latestIplTeam", label: "IPL team", format: formatText, isText: true },
  { key: "rating", label: "Rating", format: formatDecimal },
  { key: "posteriorSd", label: "± sd", format: formatDecimal },
  { key: "rawPressureImpact", label: "Pressure impact", format: formatSigned },
  { key: "rawBaselineImpact", label: "Usual impact", format: formatSigned },
  { key: "ballsPressure", label: "Pressure balls", format: formatInteger },
];
const ROLE_COLUMNS = {
  batter: [
    { key: "strikeRatePressure", label: "Pressure SR", format: (value) => formatDecimal(value, 0) },
    { key: "averagePressure", label: "Pressure avg", format: formatDecimal },
  ],
  bowler: [
    { key: "economyPressure", label: "Pressure econ", format: (value) => formatDecimal(value, 2) },
    { key: "wicketsPressure", label: "Pressure wkts", format: formatInteger },
  ],
};
const CLOSING_COLUMNS = [
  { key: "topListProbability", label: "Top-ten chance", format: formatPercent },
  { key: "dipProbability", label: "Dip chance", format: formatPercent },
];

function isListed(player, listSize) {
  return player.finalRank !== null && player.finalRank <= listSize;
}

export function filterPlayers(players, state, listSize) {
  const query = state.search.trim().toLowerCase();
  return players.filter((player) => {
    const haystack = `${player.playerName} ${player.latestIplTeam ?? ""}`.toLowerCase();
    return haystack.includes(query) && (!state.listedOnly || isListed(player, listSize));
  });
}

function plotScales(players) {
  const values = players.flatMap((player) => [player.rawBaselineImpact, player.rawPressureImpact]);
  const domain = [Math.min(...values) - DOMAIN_PADDING, Math.max(...values) + DOMAIN_PADDING];
  return {
    domain,
    x: linearScale(domain, [MARGIN.left, PLOT_WIDTH - MARGIN.right]),
    y: linearScale(domain, [PLOT_HEIGHT - MARGIN.bottom, MARGIN.top]),
  };
}

function drawAxes(svg, scales) {
  for (const tick of roundTicks(scales.domain[0], scales.domain[1], TICK_COUNT)) {
    const isZero = tick === 0;
    svg.append(svgElement("line", { class: isZero ? "baseline" : "gridline", x1: scales.x(tick), x2: scales.x(tick), y1: MARGIN.top, y2: PLOT_HEIGHT - MARGIN.bottom }));
    svg.append(svgElement("line", { class: isZero ? "baseline" : "gridline", x1: MARGIN.left, x2: PLOT_WIDTH - MARGIN.right, y1: scales.y(tick), y2: scales.y(tick) }));
    svg.append(svgElement("text", { class: "tick", x: scales.x(tick), y: PLOT_HEIGHT - MARGIN.bottom + 16, "text-anchor": "middle" }, formatSigned(tick, 0)));
    svg.append(svgElement("text", { class: "tick", x: MARGIN.left - 8, y: scales.y(tick) + 4, "text-anchor": "end" }, formatSigned(tick, 0)));
  }
  svg.append(svgElement("line", { class: "baseline", x1: scales.x(scales.domain[0]), y1: scales.y(scales.domain[0]), x2: scales.x(scales.domain[1]), y2: scales.y(scales.domain[1]) }));
  svg.append(svgElement("text", { class: "axisTitle", x: PLOT_WIDTH - MARGIN.right, y: PLOT_HEIGHT - 6, "text-anchor": "end" }, "Usual level, runs per 100 balls against average →"));
  svg.append(svgElement("text", { class: "axisTitle", x: 12, y: MARGIN.top, transform: `rotate(-90 12 ${MARGIN.top})`, "text-anchor": "end" }, "Pressure balls →"));
}

function drawPoint(svg, player, scales, isSelected, listSize) {
  const centre = { cx: scales.x(player.rawBaselineImpact), cy: scales.y(player.rawPressureImpact) };
  if (isSelected) {
    svg.append(svgElement("circle", { ...centre, r: SELECTED_RADIUS, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 2 }));
  } else if (isListed(player, listSize)) {
    svg.append(svgElement("circle", { ...centre, r: DOT_RADIUS, fill: "var(--ink)", stroke: "var(--surface)", "stroke-width": 2 }));
  } else {
    svg.append(svgElement("circle", { ...centre, r: DOT_RADIUS - 0.75, fill: "var(--surface)", stroke: "var(--inkMuted)", "stroke-width": 1.5 }));
  }
  if (isSelected || (player.finalRank !== null && player.finalRank <= LABELLED_RANKS)) {
    const flipsLeft = centre.cx > PLOT_WIDTH * LABEL_FLIP_SHARE;
    const label = svgElement("text", { x: centre.cx + (flipsLeft ? -LABEL_OFFSET : LABEL_OFFSET), y: centre.cy + (flipsLeft ? FLIPPED_LABEL_DROP : 4), "font-size": 12,
      "font-weight": isSelected ? 600 : 400, "text-anchor": flipsLeft ? "end" : "start" }, player.playerName);
    label.style.fill = "var(--ink)";
    label.style.paintOrder = "stroke";
    label.style.stroke = "var(--surface)";
    label.style.strokeWidth = "3px";
    svg.append(label);
  }
}

function nearestPlayer(event, svg, players, scales) {
  const box = svg.getBoundingClientRect();
  const pointerX = (event.clientX - box.left) * (PLOT_WIDTH / box.width);
  const pointerY = (event.clientY - box.top) * (PLOT_HEIGHT / box.height);
  let nearest = null;
  let nearestDistance = SNAP_DISTANCE;
  for (const player of players) {
    const distance = Math.hypot(scales.x(player.rawBaselineImpact) - pointerX, scales.y(player.rawPressureImpact) - pointerY);
    if (distance < nearestDistance) {
      nearest = player;
      nearestDistance = distance;
    }
  }
  return nearest;
}

function pointTooltip(player) {
  return { title: player.playerName, rows: [["Pressure balls", formatSigned(player.rawPressureImpact)],
    ["Usual level", formatSigned(player.rawBaselineImpact)], ["Rating", formatDecimal(player.rating)]] };
}

/** The pointer only has to be closest to a point, never dead-centre on it. */
export function renderScatter(container, allPlayers, shownPlayers, selectedId, listSize, onSelect) {
  const scales = plotScales(allPlayers);
  const svg = svgElement("svg", { viewBox: `0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`, role: "img",
    "aria-label": "Scatter of each player's pressure-ball impact against their usual impact. The table below lists every value." });
  drawAxes(svg, scales);
  const ordered = [...shownPlayers].sort((first, second) => (first.playerId === selectedId) - (second.playerId === selectedId));
  for (const player of ordered) {
    drawPoint(svg, player, scales, player.playerId === selectedId, listSize);
  }
  const hitLayer = svgElement("rect", { class: "hit", x: 0, y: 0, width: PLOT_WIDTH, height: PLOT_HEIGHT });
  hitLayer.addEventListener("pointermove", (event) => {
    const player = nearestPlayer(event, svg, shownPlayers, scales);
    if (player) {
      showTooltipAt(pointTooltip(player), event.clientX, event.clientY);
    } else {
      hideTooltip();
    }
  });
  hitLayer.addEventListener("pointerleave", hideTooltip);
  hitLayer.addEventListener("click", (event) => {
    const player = nearestPlayer(event, svg, shownPlayers, scales);
    if (player) {
      onSelect(player.playerId);
    }
  });
  svg.append(hitLayer);
  clearNode(container).append(svg);
}

function tableColumns(role) {
  return [...SHARED_COLUMNS, ...ROLE_COLUMNS[role], ...CLOSING_COLUMNS];
}

function sortPlayers(players, state) {
  const direction = state.sortAscending ? 1 : -1;
  return [...players].sort((first, second) => {
    const [left, right] = [first[state.sortKey], second[state.sortKey]];
    if (left === null || right === null) {
      return (left === null) - (right === null);
    }
    return (typeof left === "string" ? left.localeCompare(right) : left - right) * direction;
  });
}

function headerRow(columns, state, onSort) {
  const row = htmlElement("tr");
  for (const column of columns) {
    const cell = htmlElement("th", column.isText ? "text" : "");
    const button = htmlElement("button", "", column.label);
    button.type = "button";
    button.addEventListener("click", () => onSort(column.key));
    if (column.key === state.sortKey) {
      cell.setAttribute("aria-sort", state.sortAscending ? "ascending" : "descending");
    }
    cell.append(button);
    row.append(cell);
  }
  return row;
}

function playerRow(player, columns, isSelected, listSize, onSelect) {
  const row = htmlElement("tr");
  row.tabIndex = 0;
  row.setAttribute("aria-selected", String(isSelected));
  for (const column of columns) {
    const cell = htmlElement("td", column.isText ? "text" : "", column.format(player[column.key]));
    if (column.key === "playerName") {
      cell.className = "text name";
      cell.prepend(htmlElement("span", isListed(player, listSize) ? "mark isListed" : "mark"));
    }
    row.append(cell);
  }
  row.addEventListener("click", () => onSelect(player.playerId));
  row.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(player.playerId);
    }
  });
  return row;
}

export function renderPlayerTable(table, players, role, state, listSize, handlers) {
  const columns = tableColumns(role);
  const head = htmlElement("thead");
  head.append(headerRow(columns, state, handlers.onSort));
  const body = htmlElement("tbody");
  for (const player of sortPlayers(players, state)) {
    body.append(playerRow(player, columns, player.playerId === state.selectedId, listSize, handlers.onSelect));
  }
  clearNode(table).append(head, body);
}
