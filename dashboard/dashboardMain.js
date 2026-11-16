import { dashboardData } from "./dashboardData.js";
import { renderComparison, renderHeatmap, renderIntervalPlot, renderRepeatPlot, renderSensitivityTable } from "./evidenceSections.js";
import { filterPlayers, renderPlayerTable, renderScatter } from "./explorerSection.js";
import { renderRankedList, topListed } from "./listsSection.js";
import { renderPlayerCard } from "./playerCard.js";
import { renderRoyalsPlot, renderSquadTable } from "./royalsSection.js";
import { formatDecimal, formatInteger, formatPercent } from "./svgToolkit.js";

const FACT_FORMATS = {
  integer: formatInteger,
  percent: formatPercent,
  decimal3: (value) => formatDecimal(value, 3),
};
const DEFAULT_SORT = { sortKey: "rank", sortAscending: true };
const TEXT_SORT_KEYS = ["playerName", "latestIplTeam", "rank"];

const listSize = dashboardData.summary.topListSize;
const roles = dashboardData.roles;
const state = { role: "batter", intervalRole: "batter", search: "", listedOnly: false, selectedId: null, ...DEFAULT_SORT };

function byId(id) {
  return document.getElementById(id);
}

function resolveFact(path) {
  return path.split(".").reduce((value, key) => value[key], dashboardData);
}

function bindFacts() {
  for (const node of document.querySelectorAll("[data-fact]")) {
    const value = resolveFact(node.dataset.fact);
    const format = FACT_FORMATS[node.dataset.format];
    node.textContent = format ? format(value) : String(value);
  }
  for (const node of document.querySelectorAll("[data-count]")) {
    node.textContent = String(roles[node.dataset.count].players.length);
  }
}

function players() {
  return roles[state.role].players;
}

function selectedPlayer() {
  return players().find((player) => player.playerId === state.selectedId) ?? topListed(players(), listSize)[0];
}

function renderExplorer() {
  const shown = filterPlayers(players(), state, listSize);
  const player = selectedPlayer();
  state.selectedId = player.playerId;
  renderScatter(byId("scatterPlot"), players(), shown, state.selectedId, listSize, selectPlayer);
  renderPlayerCard(byId("playerCard"), player, state.role, players().length, listSize);
  renderPlayerTable(byId("playerTable"), shown, state.role, state, listSize, { onSelect: selectPlayer, onSort: sortBy });
  for (const button of document.querySelectorAll("[data-role]")) {
    button.setAttribute("aria-pressed", String(button.dataset.role === state.role));
  }
}

function renderIntervals() {
  renderIntervalPlot(byId("intervalPlot"), roles[state.intervalRole].players, listSize);
  for (const button of document.querySelectorAll("[data-interval-role]")) {
    button.setAttribute("aria-pressed", String(button.dataset.intervalRole === state.intervalRole));
  }
}

function selectPlayer(playerId) {
  state.selectedId = playerId;
  renderExplorer();
}

function sortBy(key) {
  const sameKey = state.sortKey === key;
  state.sortAscending = sameKey ? !state.sortAscending : TEXT_SORT_KEYS.includes(key);
  state.sortKey = key;
  renderExplorer();
}

function switchRole(role) {
  Object.assign(state, { role, selectedId: null, search: "", ...DEFAULT_SORT });
  byId("playerSearch").value = "";
  renderExplorer();
}

/** A name in the headline lists opens that player's record in the explorer. */
function openFromList(role, playerId) {
  Object.assign(state, { role, search: "", listedOnly: false, selectedId: playerId, ...DEFAULT_SORT });
  byId("playerSearch").value = "";
  byId("listedOnly").checked = false;
  renderExplorer();
  byId("explorer").scrollIntoView();
}

function renderStaticSections() {
  renderRankedList(byId("batterList"), roles.batter.players, listSize, (playerId) => openFromList("batter", playerId));
  renderRankedList(byId("bowlerList"), roles.bowler.players, listSize, (playerId) => openFromList("bowler", playerId));
  renderHeatmap(byId("heatmapPlot"), dashboardData.heatmap);
  renderComparison(byId("pressureComparison"), dashboardData.summary.comparison);
  renderRepeatPlot(byId("repeatPlot"), roles);
  renderSensitivityTable(byId("sensitivityTable"), roles);
  renderRoyalsPlot(byId("royalsPlot"), dashboardData.royals.record);
  renderSquadTable(byId("squadTable"), byId("squadNote"), dashboardData.royals,
    { batter: roles.batter.players.length, bowler: roles.bowler.players.length });
}

function wireControls() {
  for (const button of document.querySelectorAll("[data-role]")) {
    button.addEventListener("click", () => switchRole(button.dataset.role));
  }
  for (const button of document.querySelectorAll("[data-interval-role]")) {
    button.addEventListener("click", () => {
      state.intervalRole = button.dataset.intervalRole;
      renderIntervals();
    });
  }
  byId("playerSearch").addEventListener("input", (event) => {
    state.search = event.target.value;
    renderExplorer();
  });
  byId("listedOnly").addEventListener("change", (event) => {
    state.listedOnly = event.target.checked;
    renderExplorer();
  });
  // The heatmap computes its fills from the theme's ramp, so it has to be redrawn when the scheme flips.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => renderHeatmap(byId("heatmapPlot"), dashboardData.heatmap));
}

bindFacts();
renderStaticSections();
renderExplorer();
renderIntervals();
wireControls();
