"""Stage 5: static charts for the report."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from buildPressureStates import STATES_FILE
from buildRatings import ROLES, ratingFile
from pipelineConfig import CHART_DIR, OUTPUT_DIR, TOP_LIST_SIZE

SERIES_BLUE = "#2a78d6"
SERIES_ORANGE = "#eb6834"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
SEQUENTIAL_STEPS = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
DARK_CELL_SHARE = 0.55
CHART_DPI = 200
WIDE_FIGURE = (7.2, 3.6)
TALL_FIGURE = (7.2, 4.4)
RANKED_PLAYERS_SHOWN = 15
RATE_BINS = [-1, 6, 8, 10, 12, 15, 100]
RATE_LABELS = ["under 6", "6 to 8", "8 to 10", "10 to 12", "12 to 15", "over 15"]
BALL_BINS = [0, 12, 30, 60, 90, 120]
BALL_LABELS = ["1-12", "13-30", "31-60", "61-90", "91-120"]
RELIABILITY_ROWS = ["expectedPressureImpact", "rawBaselineImpact", "rawPressureImpact", "rawLift"]
RELIABILITY_LABELS = ["Headline rating", "Usual-level record", "Pressure record alone", "Lift (pressure - usual)"]
ROLE_TITLES = {"batter": "batters", "bowler": "bowlers"}


def main():
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": AXIS_LINE,
                         "axes.labelcolor": INK_SECONDARY, "xtick.color": INK_MUTED, "ytick.color": INK_SECONDARY,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})
    drawCalibration()
    drawLeverageHeatmap()
    drawReliability()
    for role in ROLES:
        ratings = pd.read_csv(ratingFile(role))
        drawPressureVersusUsual(role, ratings)
        drawRankIntervals(role, ratings)


def styledAxes(figureSize):
    figure, axes = plt.subplots(figsize=figureSize)
    axes.spines[["top", "right"]].set_visible(False)
    axes.grid(color=GRIDLINE, linewidth=0.6)
    axes.set_axisbelow(True)
    return figure, axes


def saveChart(figure, name):
    figure.tight_layout()
    figure.savefig(CHART_DIR / f"{name}.png", dpi=CHART_DPI)
    plt.close(figure)


def drawCalibration():
    calibration = pd.read_csv(OUTPUT_DIR / "winModelCalibration.csv")
    figure, axes = styledAxes((4.2, 3.6))
    axes.plot([0, 1], [0, 1], color=AXIS_LINE, linewidth=1, linestyle="--")
    series = {1: ("Batting first", SERIES_BLUE, "o"), 2: ("Chasing", SERIES_ORANGE, "s")}
    for innings, (label, colour, marker) in series.items():
        rows = calibration[calibration["innings"] == innings]
        axes.plot(rows["predicted"], rows["actual"], color=colour, marker=marker, markersize=5,
                  linewidth=2, label=label)
    axes.set_xlabel("Predicted win probability (held-out matches)")
    axes.set_ylabel("Share of those balls where the batting side won")
    axes.legend(frameon=False, loc="upper left")
    saveChart(figure, "winCalibration")


def chaseHeatmapGrid(states, aggregate="mean"):
    """Chase balls binned by required rate (rows, hardest first) and balls left (columns, most first)."""
    chase = states[(states["innings"] == 2) & states["isLegal"]].copy()
    chase["rate"] = pd.cut(chase["requiredRunRate"], RATE_BINS, labels=RATE_LABELS)
    chase["balls"] = pd.cut(chase["ballsLeft"], BALL_BINS, labels=BALL_LABELS)
    grid = chase.pivot_table(index="rate", columns="balls", values="isPressure", aggfunc=aggregate, observed=False)
    return grid.reindex(index=RATE_LABELS[::-1], columns=BALL_LABELS[::-1])


def drawLeverageHeatmap():
    grid = chaseHeatmapGrid(pd.read_pickle(STATES_FILE))
    figure, axes = plt.subplots(figsize=(5.4, 3.6))
    colourMap = LinearSegmentedColormap.from_list("sequentialBlue", SEQUENTIAL_STEPS)
    axes.imshow(grid.to_numpy(), cmap=colourMap, vmin=0, vmax=1, aspect="auto")
    for (row, column), share in np.ndenumerate(grid.to_numpy()):
        textColour = "#ffffff" if share > DARK_CELL_SHARE else INK
        axes.text(column, row, f"{share:.0%}", ha="center", va="center", color=textColour, fontsize=8.5)
    axes.set_xticks(range(len(grid.columns)), grid.columns)
    axes.set_yticks(range(len(grid.index)), grid.index)
    axes.set_xlabel("Balls left in the chase")
    axes.set_ylabel("Required runs per over")
    axes.tick_params(length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)
    saveChart(figure, "pressureHeatmap")


def drawReliability():
    figure, axes = styledAxes(WIDE_FIGURE)
    barHeight = 0.36
    positions = np.arange(len(RELIABILITY_ROWS))
    colours = {"batter": SERIES_BLUE, "bowler": SERIES_ORANGE}
    for offset, role in zip((-barHeight / 2, barHeight / 2), ROLES):
        table = pd.read_csv(OUTPUT_DIR / f"{role}SplitHalf.csv", index_col="measure")
        values = table.loc[RELIABILITY_ROWS, "halfCorrelation"]
        axes.barh(positions + offset, values, height=barHeight - 0.04, color=colours[role],
                  label=ROLE_TITLES[role].capitalize())
        for position, value in zip(positions + offset, values):
            axes.text(max(value, 0) + 0.008, position, f"{value:.2f}", va="center", color=INK_SECONDARY, fontsize=8)
    axes.axvline(0, color=AXIS_LINE, linewidth=1)
    axes.set_yticks(positions, RELIABILITY_LABELS)
    axes.invert_yaxis()
    axes.grid(axis="y", visible=False)
    axes.set_xlabel("Correlation between two random halves of the matches")
    axes.legend(frameon=False, loc="lower right")
    saveChart(figure, "splitHalfReliability")


def drawPressureVersusUsual(role, ratings):
    """Each listed player's pressure record against their usual level, with the blended rating between."""
    listed = ratings[ratings["finalRank"] <= TOP_LIST_SIZE].sort_values("finalRank")
    figure, axes = styledAxes(TALL_FIGURE)
    positions = np.arange(len(listed))
    axes.hlines(positions, listed["rawBaselineImpact"], listed["rawPressureImpact"], color=AXIS_LINE, linewidth=2)
    axes.scatter(listed["rawBaselineImpact"], positions, color=SERIES_BLUE, s=42, zorder=3,
                 edgecolor=SURFACE, linewidth=1.2, label="Usual level (non-pressure balls)")
    axes.scatter(listed["rawPressureImpact"], positions, color=SERIES_ORANGE, s=42, zorder=3, marker="s",
                 edgecolor=SURFACE, linewidth=1.2, label="Pressure balls")
    axes.scatter(listed["rating"], positions, color=INK, s=34, zorder=4, marker="D",
                 edgecolor=SURFACE, linewidth=1.2, label="Headline rating (blended, shrunk)")
    axes.axvline(0, color=AXIS_LINE, linewidth=1)
    labels = [f"{int(rank)}. {name}" for rank, name in zip(listed["finalRank"], listed["playerName"])]
    axes.set_yticks(positions, labels)
    axes.invert_yaxis()
    axes.grid(axis="y", visible=False)
    axes.set_xlabel("Runs per 100 balls better than an average player in the same situations")
    axes.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=7.5)
    saveChart(figure, f"{role}PressureVersusUsual")


def drawRankIntervals(role, ratings):
    """Bootstrap spread of each player's rank when whole matches are resampled."""
    shown = ratings.sort_values("rank").head(RANKED_PLAYERS_SHOWN)
    figure, axes = styledAxes(WIDE_FIGURE)
    positions = np.arange(len(shown))
    listedColour = np.where(shown["finalRank"] <= TOP_LIST_SIZE, SERIES_BLUE, INK_MUTED)
    axes.hlines(positions, shown["rankLow"], shown["rankHigh"], color=listedColour, linewidth=2)
    axes.scatter(shown["rankMedian"], positions, color=listedColour, s=40, zorder=3,
                 edgecolor=SURFACE, linewidth=1.2)
    axes.axvline(TOP_LIST_SIZE + 0.5, color=AXIS_LINE, linewidth=1, linestyle="--")
    labels = [f"{name}  ({probability:.0%})" for name, probability in
              zip(shown["playerName"], shown["topListProbability"])]
    axes.set_yticks(positions, labels)
    axes.invert_yaxis()
    axes.grid(axis="y", visible=False)
    axes.set_xlabel(f"Rank among eligible {ROLE_TITLES[role]}: median and 5th-95th percentile over resamples")
    saveChart(figure, f"{role}RankIntervals")


if __name__ == "__main__":
    main()
