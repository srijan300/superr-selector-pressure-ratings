import pandas as pd

from pipelineConfig import (
    ACTIVE_SINCE_DATE,
    MIN_PRESSURE_BALLS_BATTER,
    MIN_PRESSURE_BALLS_BOWLER,
    MIN_PRESSURE_OUTINGS,
    RECENCY_HALF_LIFE_DAYS,
)
from playerRating import HEADLINE_METHOD, RATING_COLUMNS, buildStatCube, estimateShrinkage, ratingComponents

MIN_PRESSURE_BALLS = {"batter": MIN_PRESSURE_BALLS_BATTER, "bowler": MIN_PRESSURE_BALLS_BOWLER}


def buildRatingTable(balls, role, pressureFlag=None, halfLifeDays=RECENCY_HALF_LIFE_DAYS,
                     method=HEADLINE_METHOD, minPressureBalls=None):
    """Rated, eligible players sorted best first, plus the pieces a bootstrap needs."""
    flag = balls["isPressure"] if pressureFlag is None else pressureFlag
    cube = buildStatCube(balls, flag, halfLifeDays)
    totals = cube.totals()
    parameters = estimateShrinkage(totals)
    table = ratingComponents(totals, parameters).set_index(cube.players)
    table["pressureBalls"] = totals["ballsPressure"]
    table["baselineBalls"] = totals["ballsBaseline"]
    table["pressureOutings"] = totals["outings"]
    table["lastMatch"] = balls.groupby("playerId")["match_date"].max().reindex(cube.players)
    threshold = MIN_PRESSURE_BALLS[role] if minPressureBalls is None else minPressureBalls
    eligible = eligibility(table, threshold).to_numpy()
    rated = table[eligible].copy()
    rated["rating"] = rated[RATING_COLUMNS[method]]
    rated = rated.sort_values("rating", ascending=False)
    rated["rank"] = range(1, len(rated) + 1)
    return rated, cube, parameters, eligible


def eligibility(table, minPressureBalls):
    """Enough pressure evidence, spread over enough matches, and still active for the next auction."""
    return ((table["pressureBalls"] >= minPressureBalls)
            & (table["pressureOutings"] >= MIN_PRESSURE_OUTINGS)
            & (table["lastMatch"] >= pd.Timestamp(ACTIVE_SINCE_DATE)))
