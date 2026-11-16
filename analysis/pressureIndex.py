import numpy as np
import pandas as pd

from pipelineConfig import LEVERAGE_OUTCOME_RUNS, PRESSURE_QUANTILE

WICKET_OUTCOME = "wicket"


def outcomeProbabilities(states):
    """League-wide chance of each legal-ball outcome, by innings and phase."""
    legal = states[states["isLegal"]]
    runClasses = np.array(LEVERAGE_OUTCOME_RUNS)
    nearest = runClasses[np.abs(legal["totalRuns"].to_numpy()[:, None] - runClasses[None, :]).argmin(axis=1)]
    outcome = np.where(legal["is_wicket"], WICKET_OUTCOME, nearest.astype(str))
    counts = pd.crosstab([legal["innings"], legal["phase"]], outcome)
    return counts.div(counts.sum(axis=1), axis=0)


def addWinProbabilityAndLeverage(states, winModel):
    """Leverage = expected absolute swing in win probability on the delivery about to be bowled."""
    states = states.copy()
    states["wpBefore"] = stateWinProbability(states, winModel, 0, 0, 0)
    states["wpAfter"] = stateWinProbability(
        states, winModel, states["totalRuns"], states["is_wicket"].astype(int), states["isLegal"].astype(int))
    probabilities = outcomeProbabilities(states)
    keys = pd.MultiIndex.from_arrays([states["innings"], states["phase"]])
    leverage = np.zeros(len(states))
    for outcome in probabilities.columns:
        isWicket = outcome == WICKET_OUTCOME
        runs = 0 if isWicket else int(outcome)
        swing = np.abs(stateWinProbability(states, winModel, runs, int(isWicket), 1) - states["wpBefore"])
        leverage += probabilities[outcome].reindex(keys).to_numpy() * swing.to_numpy()
    states["leverage"] = leverage
    return states


def stateWinProbability(states, winModel, addedRuns, addedWickets, ballsUsed):
    return winModel.predictState(
        states["innings"], states["runsBefore"] + addedRuns, states["wicketsBefore"] + addedWickets,
        states["ballsLeft"] - ballsUsed, states["target"].fillna(0), states["isIpl"], states["seasonYear"])


def pressureThreshold(states, quantile=PRESSURE_QUANTILE):
    return states.loc[states["isLegal"], "leverage"].quantile(quantile)


def flagPressure(states, quantile=PRESSURE_QUANTILE):
    return states["leverage"] >= pressureThreshold(states, quantile)
