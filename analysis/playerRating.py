from dataclasses import dataclass

import numpy as np
import pandas as pd

from pipelineConfig import (
    LOWER_BOUND_DEVIATIONS,
    MIN_BALLS_FOR_VARIANCE_ESTIMATE,
    MIN_OUTING_PRESSURE_BALLS,
    OUTING_PRIOR_STRENGTH,
    PER_HUNDRED,
    RECENCY_HALF_LIFE_DAYS,
)

SITUATIONS = ("Pressure", "Baseline")
HEADLINE_METHOD = "hierarchical"
RATING_COLUMNS = {"hierarchical": "expectedPressureImpact", "pressureOnly": "pressureOnlyEstimate",
                  "lowerBound": "conservativeEstimate"}


@dataclass
class StatCube:
    """Per player-by-match sufficient statistics, so any resample of matches is one matrix product."""
    players: pd.Index
    matches: pd.Index
    arrays: dict

    def totals(self, matchCounts=None):
        counts = np.ones(len(self.matches)) if matchCounts is None else matchCounts
        return {name: array @ counts for name, array in self.arrays.items()}


@dataclass
class ShrinkageParameters:
    pressureBallVariance: float
    baselineBallVariance: float
    baselineSignalVariance: float
    liftSignalVariance: float
    liftSignalVarianceUntruncated: float
    leagueOutingRate: float


def recencyWeights(dates, halfLifeDays=RECENCY_HALF_LIFE_DAYS):
    if halfLifeDays is None:
        return np.ones(len(dates))
    ageDays = (dates.max() - dates).dt.days.to_numpy()
    return 0.5 ** (ageDays / halfLifeDays)


def buildStatCube(balls, pressureFlag, halfLifeDays=RECENCY_HALF_LIFE_DAYS):
    playerCodes, players = pd.factorize(balls["playerId"])
    matchCodes, matches = pd.factorize(balls["match_id"])
    shape = (len(players), len(matches))
    cell = playerCodes * shape[1] + matchCodes
    weight = recencyWeights(balls["match_date"], halfLifeDays)
    impact = balls["impact"].to_numpy()
    pressure = np.asarray(pressureFlag, dtype=bool)
    arrays = {}
    for situation, mask in zip(SITUATIONS, (pressure, ~pressure)):
        values = {"balls": np.ones(len(balls)), "weight": weight, "squaredWeight": weight ** 2,
                  "weightedImpact": weight * impact, "weightedSquare": weight * impact ** 2, "impactSum": impact}
        for name, column in values.items():
            arrays[f"{name}{situation}"] = cellSums(cell[mask], column[mask], shape)
    matchWeight = cellSums(matchCodes, weight, (len(matches),)) / np.bincount(matchCodes, minlength=len(matches))
    isOuting = arrays["ballsPressure"] >= MIN_OUTING_PRESSURE_BALLS
    arrays["outings"] = isOuting.astype(float)
    arrays["outingWeight"] = isOuting * matchWeight[None, :]
    arrays["outingWinWeight"] = arrays["outingWeight"] * (arrays["impactSumPressure"] > 0)
    return StatCube(pd.Index(players), pd.Index(matches), arrays)


def cellSums(cell, values, shape):
    size = int(np.prod(shape))
    return np.bincount(cell, weights=values, minlength=size).reshape(shape)


def rawMeasures(totals):
    """Recency-weighted means and effective sample sizes per player, before any shrinkage."""
    measures = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        for situation in SITUATIONS:
            weight = totals[f"weight{situation}"]
            measures[f"mean{situation}"] = totals[f"weightedImpact{situation}"] / weight
            measures[f"effectiveBalls{situation}"] = weight ** 2 / totals[f"squaredWeight{situation}"]
        measures["outingRate"] = totals["outingWinWeight"] / totals["outingWeight"]
    return measures


def estimateShrinkage(totals):
    """Method of moments: variance of true skill = variance of observed means minus sampling noise."""
    measures = rawMeasures(totals)
    ballVariance = {}
    for situation in SITUATIONS:
        weight = totals[f"weight{situation}"].sum()
        mean = totals[f"weightedImpact{situation}"].sum() / weight
        ballVariance[situation] = totals[f"weightedSquare{situation}"].sum() / weight - mean ** 2
    enough = ((measures["effectiveBallsPressure"] >= MIN_BALLS_FOR_VARIANCE_ESTIMATE)
              & (measures["effectiveBallsBaseline"] >= MIN_BALLS_FOR_VARIANCE_ESTIMATE))
    pressureNoise = ballVariance["Pressure"] / measures["effectiveBallsPressure"][enough]
    baselineNoise = ballVariance["Baseline"] / measures["effectiveBallsBaseline"][enough]
    lift = (measures["meanPressure"] - measures["meanBaseline"])[enough]
    baselineSignal = max(np.var(measures["meanBaseline"][enough]) - baselineNoise.mean(), 0.0)
    liftSignal = np.var(lift) - (pressureNoise + baselineNoise).mean()
    leagueRate = totals["outingWinWeight"].sum() / totals["outingWeight"].sum()
    return ShrinkageParameters(ballVariance["Pressure"], ballVariance["Baseline"], baselineSignal,
                               max(liftSignal, 0.0), liftSignal, leagueRate)


def hierarchicalPressureEstimate(measures, parameters):
    """Posterior mean and sd of true pressure impact, where pressure skill = usual skill + a personal lift.

    The usual-level record and the pressure record are both noisy readings of the same player; each is
    weighted by its precision and by how much players genuinely differ on it.
    """
    usual, lift = parameters.baselineSignalVariance, parameters.liftSignalVariance
    with np.errstate(divide="ignore", invalid="ignore"):
        baselineNoise = parameters.baselineBallVariance / measures["effectiveBallsBaseline"]
        pressureNoise = parameters.pressureBallVariance / measures["effectiveBallsPressure"]
        determinant = (usual + baselineNoise) * (usual + lift + pressureNoise) - usual ** 2
        baselineWeight = (usual * (usual + lift + pressureNoise) - (usual + lift) * usual) / determinant
        pressureWeight = ((usual + lift) * (usual + baselineNoise) - usual ** 2) / determinant
        mean = baselineWeight * measures["meanBaseline"] + pressureWeight * measures["meanPressure"]
        variance = (usual + lift) - (baselineWeight * usual + pressureWeight * (usual + lift))
        pressureOnlyTrust = (usual + lift) / (usual + lift + pressureNoise)
    return {"mean": np.nan_to_num(mean), "sd": np.sqrt(np.clip(np.nan_to_num(variance), 0.0, None)),
            "baselineWeight": baselineWeight, "pressureWeight": pressureWeight,
            "pressureOnly": np.nan_to_num(pressureOnlyTrust * measures["meanPressure"])}


def ratingComponents(totals, parameters):
    """Everything reported per player, in runs per 100 balls above an average player in the same situations."""
    measures = rawMeasures(totals)
    estimate = hierarchicalPressureEstimate(measures, parameters)
    consistency = ((totals["outingWinWeight"] + OUTING_PRIOR_STRENGTH * parameters.leagueOutingRate)
                   / (totals["outingWeight"] + OUTING_PRIOR_STRENGTH))
    return pd.DataFrame({
        "expectedPressureImpact": estimate["mean"] * PER_HUNDRED,
        "posteriorSd": estimate["sd"] * PER_HUNDRED,
        "conservativeEstimate": (estimate["mean"] - LOWER_BOUND_DEVIATIONS * estimate["sd"]) * PER_HUNDRED,
        "pressureOnlyEstimate": estimate["pressureOnly"] * PER_HUNDRED,
        "rawPressureImpact": measures["meanPressure"] * PER_HUNDRED,
        "rawBaselineImpact": measures["meanBaseline"] * PER_HUNDRED,
        "rawLift": (measures["meanPressure"] - measures["meanBaseline"]) * PER_HUNDRED,
        "pressureWeight": estimate["pressureWeight"],
        "baselineWeight": estimate["baselineWeight"],
        "consistency": consistency,
        "rawOutingRate": measures["outingRate"],
    })
