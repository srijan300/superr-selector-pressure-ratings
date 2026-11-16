"""Stage 3: player pressure ratings, their uncertainty, and how far they move under other assumptions."""
from dataclasses import asdict

import pandas as pd

from buildBallImpacts import BATTER_BALLS_FILE, BOWLER_BALLS_FILE
from dataLoader import loadBalls, loadPlayerNames
from descriptiveStats import batterDescriptives, bowlerDescriptives
from pipelineConfig import DIP_PROBABILITY_GATE, OUTPUT_DIR, TOP_LIST_SIZE
from ratingTable import buildRatingTable
from reliabilityChecks import (
    bootstrapRatings,
    compareToHeadline,
    heldOutPrediction,
    sensitivityVariants,
    splitHalfReliability,
)

ROLES = ("batter", "bowler")
BALL_FILES = {"batter": BATTER_BALLS_FILE, "bowler": BOWLER_BALLS_FILE}
DESCRIPTIVE_BUILDERS = {"batter": batterDescriptives, "bowler": bowlerDescriptives}
PREVIEW_COLUMNS = ["playerName", "finalRank", "rating", "posteriorSd", "rawPressureImpact", "rawBaselineImpact",
                   "pressureWeight", "pressureBalls", "baselineBalls", "rankLow", "rankHigh",
                   "topListProbability", "dipProbability"]
PREVIEW_ROWS = 16


def ratingFile(role):
    return OUTPUT_DIR / f"{role}Ratings.csv"


def main():
    names = loadPlayerNames(loadBalls())
    for role in ROLES:
        balls = pd.read_pickle(BALL_FILES[role])
        rated, cube, parameters, eligible = buildRatingTable(balls, role)
        rated = rated.join(bootstrapRatings(cube, parameters, eligible))
        rated = addFinalRank(rated)
        rated.insert(0, "playerName", names.reindex(rated.index))
        rated = rated.drop(columns="lastMatch").join(DESCRIPTIVE_BUILDERS[role](balls))
        rated.to_csv(ratingFile(role), index_label="playerId")
        pd.Series(asdict(parameters)).to_csv(OUTPUT_DIR / f"{role}Shrinkage.csv", header=["value"])
        splitHalfReliability(cube, parameters, eligible).to_csv(
            OUTPUT_DIR / f"{role}SplitHalf.csv", index_label="measure")
        prediction = heldOutPrediction(cube, parameters, eligible)
        prediction.to_csv(OUTPUT_DIR / f"{role}HeldOutPrediction.csv", index_label="predictor")
        sensitivity = compareToHeadline(rated, sensitivityVariants(balls, role))
        sensitivity.to_csv(OUTPUT_DIR / f"{role}Sensitivity.csv", index=False)
        print(f"== {role}: {len(rated)} eligible players")
        print(rated[PREVIEW_COLUMNS].head(PREVIEW_ROWS).round(3).to_string())
        print(sensitivity.round(3).to_string(index=False))
        print(prediction.round(3).to_string())


def addFinalRank(rated):
    """The submitted order: rating order among players whose own pressure record backs the estimate.

    A listed player must have been above average on pressure balls and must not credibly dip below their usual level.
    """
    rated["provenUnderPressure"] = rated["rawPressureImpact"] > 0
    rated["passesDipGate"] = rated["dipProbability"] < DIP_PROBABILITY_GATE
    passesGate = rated["provenUnderPressure"] & rated["passesDipGate"]
    rated["finalRank"] = passesGate.cumsum().where(passesGate)
    rated["inTopList"] = rated["finalRank"] <= TOP_LIST_SIZE
    return rated


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    main()
