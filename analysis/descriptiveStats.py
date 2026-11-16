import numpy as np

from pipelineConfig import BALLS_PER_OVER, PER_HUNDRED

BOUNDARY_RUNS = 4


def batterDescriptives(balls):
    """Conventional scorecard numbers under pressure and otherwise, for evidence tables."""
    frame = balls.assign(winAdded=balls["wpAfter"] - balls["wpBefore"],
                         isDot=balls["runs"] == 0, isBoundary=balls["runs"] >= BOUNDARY_RUNS,
                         isOut=balls["strikerOut"])
    grouped = frame.groupby(["playerId", "isPressure"]).agg(
        balls=("isLegal", "sum"), runs=("runs", "sum"), outs=("isOut", "sum"), dotShare=("isDot", "mean"),
        boundaryShare=("isBoundary", "mean"), winAdded=("winAdded", "sum"), iplShare=("isIpl", "mean"))
    with np.errstate(divide="ignore", invalid="ignore"):
        grouped["strikeRate"] = grouped["runs"] / grouped["balls"] * PER_HUNDRED
        grouped["average"] = grouped["runs"] / grouped["outs"].where(grouped["outs"] > 0)
    return flattenSituations(grouped).join(careerSpan(balls))


def bowlerDescriptives(balls):
    frame = balls.assign(winAdded=balls["wpBefore"] - balls["wpAfter"],
                         isDot=balls["bowlerRuns"] == 0, isBoundary=balls["bowlerRuns"] >= BOUNDARY_RUNS)
    grouped = frame.groupby(["playerId", "isPressure"]).agg(
        balls=("isLegal", "sum"), runs=("bowlerRuns", "sum"), wickets=("bowlerWicket", "sum"),
        dotShare=("isDot", "mean"), boundaryShare=("isBoundary", "mean"), winAdded=("winAdded", "sum"),
        iplShare=("isIpl", "mean"))
    with np.errstate(divide="ignore", invalid="ignore"):
        grouped["economy"] = grouped["runs"] / grouped["balls"] * BALLS_PER_OVER
        grouped["ballsPerWicket"] = grouped["balls"] / grouped["wickets"].where(grouped["wickets"] > 0)
    result = flattenSituations(grouped).join(careerSpan(balls))
    return result.join(balls.groupby("playerId")["pace_or_spin"].agg(lambda kinds: kinds.mode().iloc[0]))


def flattenSituations(grouped):
    wide = grouped.unstack("isPressure")
    labels = {True: "Pressure", False: "Baseline"}
    wide.columns = [f"{name}{labels[flag]}" for name, flag in wide.columns]
    return wide


def careerSpan(balls):
    return balls.groupby("playerId").agg(
        matches=("match_id", "nunique"), firstMatch=("match_date", "min"), lastMatch=("match_date", "max"))
