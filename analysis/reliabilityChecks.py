import numpy as np
import pandas as pd

from pipelineConfig import (
    BOOTSTRAP_ROUNDS,
    IPL_ONLY_MIN_PRESSURE_BALLS,
    PRESSURE_QUANTILE_ALTERNATIVES,
    RANDOM_SEED,
    SPLIT_HALF_ROUNDS,
    TOP_LIST_SIZE,
)
from playerRating import HEADLINE_METHOD, RATING_COLUMNS, ratingComponents
from ratingTable import buildRatingTable

RANK_INTERVAL = (5, 95)
SPLIT_HALF_MEASURES = {"expectedPressureImpact": "headline rating (pressure + usual level)",
                       "rawPressureImpact": "pressure-ball record alone",
                       "rawBaselineImpact": "usual-level record alone",
                       "rawLift": "lift (pressure minus usual)",
                       "rawOutingRate": "share of pressure outings above expectation"}
PREDICTORS = {"expectedPressureImpact": "headline rating (pressure + usual level)",
              "pressureOnlyEstimate": "pressure-ball record alone",
              "rawBaselineImpact": "usual-level record alone"}
CRUNCH_REQUIRED_RATE = 9.0
CRUNCH_BALLS_LEFT = 60
LIVE_WIN_PROBABILITY = (0.10, 0.90)
COLLAPSE_POWERPLAY_WICKETS = 3
COLLAPSE_MIDDLE_WICKETS = 5
COLLAPSE_LAST_BALLS_LEFT = 30
POWERPLAY_BALLS_LEFT = 84


def bootstrapRatings(cube, parameters, eligible):
    """Resample whole matches, so a player's good and bad days move together as they do in reality."""
    generator = np.random.default_rng(RANDOM_SEED)
    matchCount = len(cube.matches)
    ranks, lifts = [], []
    for _ in range(BOOTSTRAP_ROUNDS):
        counts = generator.multinomial(matchCount, np.full(matchCount, 1.0 / matchCount)).astype(float)
        components = ratingComponents(cube.totals(counts), parameters)[eligible]
        ranks.append(components[RATING_COLUMNS[HEADLINE_METHOD]].rank(ascending=False).to_numpy())
        lifts.append(components["rawLift"].to_numpy())
    ranks, lifts = np.array(ranks), np.array(lifts)
    return pd.DataFrame({
        "rankLow": np.percentile(ranks, RANK_INTERVAL[0], axis=0),
        "rankMedian": np.median(ranks, axis=0),
        "rankHigh": np.percentile(ranks, RANK_INTERVAL[1], axis=0),
        "topListProbability": (ranks <= TOP_LIST_SIZE).mean(axis=0),
        "dipProbability": (lifts < 0).mean(axis=0),
        "liftLow": np.nanpercentile(lifts, RANK_INTERVAL[0], axis=0),
        "liftHigh": np.nanpercentile(lifts, RANK_INTERVAL[1], axis=0),
    }, index=cube.players[eligible])


def splitHalfReliability(cube, parameters, eligible):
    """Correlation of each measure between two random halves of the matches, across eligible players."""
    generator = np.random.default_rng(RANDOM_SEED)
    matchCount = len(cube.matches)
    correlations = {name: [] for name in SPLIT_HALF_MEASURES}
    for _ in range(SPLIT_HALF_ROUNDS):
        firstHalf = (generator.permutation(matchCount) < matchCount // 2).astype(float)
        halves = [ratingComponents(cube.totals(half), parameters)[eligible] for half in (firstHalf, 1.0 - firstHalf)]
        for name in correlations:
            correlations[name].append(halves[0][name].corr(halves[1][name]))
    halfCorrelation = pd.Series({name: np.mean(values) for name, values in correlations.items()})
    fullSample = 2 * halfCorrelation / (1 + halfCorrelation)
    return pd.DataFrame({"description": pd.Series(SPLIT_HALF_MEASURES), "halfCorrelation": halfCorrelation,
                         "fullSampleReliability": fullSample})


def heldOutPrediction(cube, parameters, eligible):
    """How well each estimate, built on one half of the matches, predicts pressure impact in the other half."""
    generator = np.random.default_rng(RANDOM_SEED)
    matchCount = len(cube.matches)
    correlations = {name: [] for name in PREDICTORS}
    for _ in range(SPLIT_HALF_ROUNDS):
        firstHalf = (generator.permutation(matchCount) < matchCount // 2).astype(float)
        fitted = ratingComponents(cube.totals(firstHalf), parameters)[eligible]
        heldOut = ratingComponents(cube.totals(1.0 - firstHalf), parameters)[eligible]["rawPressureImpact"]
        for name in correlations:
            correlations[name].append(fitted[name].corr(heldOut))
    return pd.DataFrame({"description": pd.Series(PREDICTORS),
                         "correlationWithHeldOutPressureImpact":
                             pd.Series({name: np.mean(values) for name, values in correlations.items()})})


def situationalPressureFlag(balls):
    """A rule-based pressure definition, used only to test the leverage-based one against instinct."""
    live = balls["wpBefore"].between(*LIVE_WIN_PROBABILITY)
    crunch = ((balls["innings"] == 2) & (balls["requiredRunRate"] >= CRUNCH_REQUIRED_RATE)
              & (balls["ballsLeft"] <= CRUNCH_BALLS_LEFT))
    earlyCollapse = (balls["ballsLeft"] > POWERPLAY_BALLS_LEFT) & (balls["wicketsBefore"] >= COLLAPSE_POWERPLAY_WICKETS)
    midCollapse = (balls["ballsLeft"] > COLLAPSE_LAST_BALLS_LEFT) & (balls["wicketsBefore"] >= COLLAPSE_MIDDLE_WICKETS)
    return live & (crunch | earlyCollapse | midCollapse)


def sensitivityVariants(balls, role):
    """Each variant returns its own rating table; compared against the headline ranking afterwards."""
    variants = {}
    legalLeverage = balls.loc[balls["isLegal"], "leverage"]
    for quantile in PRESSURE_QUANTILE_ALTERNATIVES:
        flag = balls["leverage"] >= legalLeverage.quantile(quantile)
        variants[f"Pressure = top {round((1 - quantile) * 100)}% of leverage"] = buildRatingTable(balls, role, flag)[0]
    variants["Rule-based pressure (crunch chase or collapse)"] = buildRatingTable(
        balls, role, situationalPressureFlag(balls), minPressureBalls=IPL_ONLY_MIN_PRESSURE_BALLS)[0]
    variants["No recency weighting"] = buildRatingTable(balls, role, halfLifeDays=None)[0]
    variants["IPL matches only"] = buildRatingTable(
        balls[balls["isIpl"]], role, minPressureBalls=IPL_ONLY_MIN_PRESSURE_BALLS)[0]
    variants["Conservative ranking (estimate minus 1 sd)"] = buildRatingTable(balls, role, method="lowerBound")[0]
    variants["Pressure record alone (no usual-level prior)"] = buildRatingTable(balls, role, method="pressureOnly")[0]
    return variants


def compareToHeadline(headline, variants):
    rows = []
    headlineTop = set(headline.index[:TOP_LIST_SIZE])
    for label, table in variants.items():
        common = headline.index.intersection(table.index)
        rows.append({
            "variant": label,
            "eligiblePlayers": len(table),
            "topListOverlap": len(headlineTop & set(table.index[:TOP_LIST_SIZE])),
            "headlineTopStillEligible": len(headlineTop & set(table.index)),
            "rankCorrelation": headline.loc[common, "rank"].corr(table.loc[common, "rank"], method="spearman"),
        })
    return pd.DataFrame(rows)
