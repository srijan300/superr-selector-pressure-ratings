const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const TOOLTIP_OFFSET = 14;
const VIEWPORT_MARGIN = 8;
const MISSING_TEXT = "-";

export function svgElement(name, attributes = {}, textContent = null) {
  const element = document.createElementNS(SVG_NAMESPACE, name);
  for (const [key, value] of Object.entries(attributes)) {
    element.setAttribute(key, value);
  }
  if (textContent !== null) {
    element.textContent = textContent;
  }
  return element;
}

export function htmlElement(tag, className = "", textContent = null) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (textContent !== null) {
    element.textContent = textContent;
  }
  return element;
}

export function clearNode(node) {
  node.replaceChildren();
  return node;
}

export function linearScale([domainStart, domainEnd], [rangeStart, rangeEnd]) {
  const slope = (rangeEnd - rangeStart) / (domainEnd - domainStart);
  return (value) => rangeStart + (value - domainStart) * slope;
}

export function roundTicks(minimum, maximum, targetCount) {
  const roughStep = (maximum - minimum) / targetCount;
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const step = [1, 2, 2.5, 5, 10].map((multiple) => multiple * magnitude).find((candidate) => candidate >= roughStep);
  const ticks = [];
  for (let tick = Math.ceil(minimum / step) * step; tick <= maximum + step / 1e6; tick += step) {
    ticks.push(Number(tick.toFixed(6)));
  }
  return ticks;
}

function isMissing(value) {
  return value === null || value === undefined || Number.isNaN(value);
}

export function formatDecimal(value, decimals = 1) {
  return isMissing(value) ? MISSING_TEXT : value.toLocaleString("en-GB", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function formatSigned(value, decimals = 1) {
  if (isMissing(value)) {
    return MISSING_TEXT;
  }
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return sign + formatDecimal(Math.abs(value), decimals);
}

export function formatInteger(value) {
  return formatDecimal(value, 0);
}

export function formatPercent(value, decimals = 0) {
  return isMissing(value) ? MISSING_TEXT : `${formatDecimal(value * 100, decimals)}%`;
}

export function formatText(value) {
  return isMissing(value) ? MISSING_TEXT : String(value);
}

export function cssVariable(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function tooltipNode() {
  return document.getElementById("tooltip");
}

function fillTooltip(content) {
  const tooltip = clearNode(tooltipNode());
  tooltip.append(htmlElement("strong", "", content.title));
  for (const [label, value] of content.rows) {
    const row = htmlElement("span");
    row.append(htmlElement("b", "", value), document.createTextNode(label));
    tooltip.append(row);
  }
  tooltip.hidden = false;
  return tooltip;
}

function placeTooltip(tooltip, left, top) {
  const box = tooltip.getBoundingClientRect();
  const maxLeft = window.innerWidth - box.width - VIEWPORT_MARGIN;
  const maxTop = window.innerHeight - box.height - VIEWPORT_MARGIN;
  tooltip.style.left = `${Math.max(VIEWPORT_MARGIN, Math.min(left, maxLeft))}px`;
  tooltip.style.top = `${Math.max(VIEWPORT_MARGIN, Math.min(top, maxTop))}px`;
}

export function showTooltipAt(content, clientX, clientY) {
  placeTooltip(fillTooltip(content), clientX + TOOLTIP_OFFSET, clientY + TOOLTIP_OFFSET);
}

export function hideTooltip() {
  tooltipNode().hidden = true;
}

/** Same details on hover and on keyboard focus; contentBuilder returns {title, rows: [[label, value]]}. */
export function attachTooltip(element, contentBuilder) {
  element.addEventListener("pointermove", (event) => showTooltipAt(contentBuilder(), event.clientX, event.clientY));
  element.addEventListener("pointerleave", hideTooltip);
  element.addEventListener("focus", () => {
    const box = element.getBoundingClientRect();
    showTooltipAt(contentBuilder(), box.right, box.top);
  });
  element.addEventListener("blur", hideTooltip);
}
