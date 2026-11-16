import { attachTooltip, clearNode, formatDecimal, formatPercent, formatText, htmlElement, linearScale, svgElement } from "./svgToolkit.js";

const STRIP_WIDTH = 140;
const STRIP_HEIGHT = 20;
const STRIP_PADDING = 6;
const DOT_RADIUS = 4.5;
const NO_TEAM_TEXT = "No IPL squad";

function listedPlayers(players) {
  return players.filter((player) => player.finalRank !== null).sort((first, second) => first.finalRank - second.finalRank);
}

export function topListed(players, listSize) {
  return listedPlayers(players).slice(0, listSize);
}

function ratingStrip(player, scale) {
  const middle = STRIP_HEIGHT / 2;
  const svg = svgElement("svg", { viewBox: `0 0 ${STRIP_WIDTH} ${STRIP_HEIGHT}`, "aria-hidden": "true" });
  svg.append(svgElement("line", { class: "gridline", x1: scale(0), x2: STRIP_WIDTH - STRIP_PADDING, y1: middle, y2: middle }));
  svg.append(svgElement("line", { class: "baseline", x1: scale(0), x2: scale(0), y1: 3, y2: STRIP_HEIGHT - 3 }));
  svg.append(svgElement("line", {
    x1: scale(Math.max(player.rating - player.posteriorSd, 0)), x2: scale(player.rating + player.posteriorSd),
    y1: middle, y2: middle, stroke: "var(--ink)", "stroke-width": 2, "stroke-linecap": "round",
  }));
  svg.append(svgElement("circle", { cx: scale(player.rating), cy: middle, r: DOT_RADIUS, fill: "var(--ink)", stroke: "var(--plane)", "stroke-width": 2 }));
  return svg;
}

function listTooltip(player) {
  return {
    title: player.playerName,
    rows: [
      ["Rating", formatDecimal(player.rating)],
      ["Standard deviation", formatDecimal(player.posteriorSd)],
      ["Chance of a top-ten place", formatPercent(player.topListProbability)],
      ["Rank range", `${formatDecimal(player.rankLow, 0)} to ${formatDecimal(player.rankHigh, 0)}`],
    ],
  };
}

/** The ranked list is both the headline and the way in to a player's full record. */
export function renderRankedList(container, players, listSize, onSelect) {
  const listed = topListed(players, listSize);
  const widest = Math.max(...listed.map((player) => player.rating + player.posteriorSd));
  const scale = linearScale([0, widest], [STRIP_PADDING, STRIP_WIDTH - STRIP_PADDING]);
  clearNode(container);
  for (const player of listed) {
    const button = htmlElement("button");
    button.type = "button";
    const name = htmlElement("span", "rankName", player.playerName);
    name.append(htmlElement("span", "rankTeam", formatText(player.latestIplTeam ?? NO_TEAM_TEXT)));
    button.append(htmlElement("span", "rankNumber", String(player.finalRank)), name, ratingStrip(player, scale),
      htmlElement("span", "rankValue", formatDecimal(player.rating)));
    button.addEventListener("click", () => onSelect(player.playerId));
    attachTooltip(button, () => listTooltip(player));
    const item = htmlElement("li");
    item.append(button);
    container.append(item);
  }
}
