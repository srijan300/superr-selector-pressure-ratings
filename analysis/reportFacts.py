"""Every number printed in the report is read here from the pipeline's own outputs, never typed by hand."""
import pandas as pd

from buildPressureStates import STATES_FILE
from buildRatings import ROLES, ratingFile
from dataLoader import loadBalls, loadMatches
from matchState import buildBallStates
from pipelineConfig import DATA_DIR, OUTPUT_DIR, TOP_LIST_SIZE
from pressureIndex import pressureThreshold
from validateState import validateAgainstResults

ROYALS_RECORD_FROM_SEASON = 2024
BOUNDARY_RUNS = 4


def gatherFacts():
    matches = loadMatches()
    states = pd.read_pickle(STATES_FILE)
    facts = {"data": dataFacts(matches, states), "pressure": pressureFacts(states),
             "winMetrics": pd.read_csv(OUTPUT_DIR / "winModelMetrics.csv").set_index("innings"),
             "royalsSquad": pd.read_csv(OUTPUT_DIR / "royalsSquad.csv"),
             "royalsRecord": royalsPooledRecord()}
    for role in ROLES:
        facts[role] = roleFacts(role)
    return facts


def dataFacts(matches, states):
    rawBalls = pd.read_csv(DATA_DIR / "ball_by_ball.csv", usecols=["match_id", "innings"])
    validation = validateAgainstResults(buildBallStates(loadBalls(), matches), matches)[0]
    usedMatches = states.drop_duplicates("match_id")
    return {
        "listedMatches": len(matches), "rawBalls": len(rawBalls),
        "matchesWithBalls": rawBalls["match_id"].nunique(),
        "superOverBalls": int((rawBalls["innings"] > 2).sum()),
        "rainRevisedMatches": int((matches["isRainRevised"] & matches["match_id"].isin(rawBalls["match_id"])).sum()),
        "usedMatches": len(usedMatches), "usedBalls": len(states),
        "usedIplMatches": int(usedMatches["isIpl"].sum()),
        "usedInternationalMatches": int(usedMatches["isInternational"].sum()),
        "firstDate": states["match_date"].min(), "lastDate": states["match_date"].max(),
        "resultsChecked": validation["resultsChecked"], "resultMismatches": validation["mismatches"],
    }


def pressureFacts(states):
    legal = states[states["isLegal"]].assign(
        swing=(states["wpAfter"] - states["wpBefore"]).abs(), isDot=states["totalRuns"] == 0,
        isBoundary=states["runs"] >= BOUNDARY_RUNS)
    comparison = legal.groupby("isPressure").agg(
        balls=("swing", "size"), meanSwing=("swing", "mean"), runsPerBall=("totalRuns", "mean"),
        wicketRate=("is_wicket", "mean"), dotRate=("isDot", "mean"), boundaryRate=("isBoundary", "mean"))
    pressure = legal[legal["isPressure"]]
    return {
        "threshold": pressureThreshold(states), "comparison": comparison,
        "pressureBalls": len(pressure),
        "chaseShareOfPressure": (pressure["innings"] == 2).mean(),
        "shareOfChaseBalls": legal.loc[legal["innings"] == 2, "isPressure"].mean(),
        "shareOfFirstInningsBalls": legal.loc[legal["innings"] == 1, "isPressure"].mean(),
        "firstInningsLeverage": legal.loc[legal["innings"] == 1, "leverage"].quantile([0.1, 0.5, 0.9]),
        "chaseLeverage": legal.loc[legal["innings"] == 2, "leverage"].quantile([0.1, 0.5, 0.9]),
    }


def roleFacts(role):
    ratings = pd.read_csv(ratingFile(role))
    listed = ratings[ratings["finalRank"] <= TOP_LIST_SIZE].sort_values("finalRank")
    cutoffRank = listed["rank"].max()
    skipped = ratings[(ratings["rank"] < cutoffRank) & ratings["finalRank"].isna()]
    return {
        "ratings": ratings, "listed": listed, "skipped": skipped,
        "shrinkage": pd.read_csv(OUTPUT_DIR / f"{role}Shrinkage.csv", index_col=0)["value"],
        "splitHalf": pd.read_csv(OUTPUT_DIR / f"{role}SplitHalf.csv", index_col="measure"),
        "heldOut": pd.read_csv(OUTPUT_DIR / f"{role}HeldOutPrediction.csv", index_col="predictor"),
        "sensitivity": pd.read_csv(OUTPUT_DIR / f"{role}Sensitivity.csv"),
        "profiles": pd.read_csv(OUTPUT_DIR / f"{role}Profiles.csv").set_index("playerId"),
    }


def royalsPooledRecord():
    """Royals against the other nine teams on IPL pressure balls, recent seasons pooled, by phase."""
    record = pd.read_csv(OUTPUT_DIR / "royalsPressureRecord.csv")
    record = record[record["seasonYear"] >= ROYALS_RECORD_FROM_SEASON]
    record["weighted"] = record["balls"] * record["impactPer100"]
    pooled = record.groupby(["discipline", "phase", "side"]).agg(balls=("balls", "sum"), weighted=("weighted", "sum"))
    pooled["impactPer100"] = pooled["weighted"] / pooled["balls"]
    return pooled.drop(columns="weighted").unstack("side")
