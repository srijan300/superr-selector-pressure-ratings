import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from pipelineConfig import (
    BALLS_PER_INNINGS,
    CROSS_VALIDATION_FOLDS,
    RANDOM_SEED,
    WICKETS_PER_INNINGS,
    WIN_MODEL_ITERATIONS,
    WIN_MODEL_LEARNING_RATE,
    WIN_MODEL_MIN_LEAF,
)
from resourceModel import ResourceModel

CHASE_FEATURES = ["runsRequired", "ballsLeft", "wicketsInHand", "isIpl"]
CHASE_MONOTONE = [-1, 1, 1, 0]
CALIBRATION_BINS = 10
TIED_CHASE_PROBABILITY = 0.5
LOGISTIC_MAX_ITERATIONS = 2000


class FirstInningsModel:
    """Win probability batting first: logistic on the projected total (runs so far + expected resource)."""

    def __init__(self):
        self.resource = ResourceModel()
        self.logistic = make_pipeline(StandardScaler(), LogisticRegression(max_iter=LOGISTIC_MAX_ITERATIONS))

    def fit(self, states):
        self.resource.fit(states)
        first = states[(states["innings"] == 1) & states["hasResult"]]
        design = self.designMatrix(first["runsBefore"], first["wicketsBefore"], first["ballsLeft"],
                                   first["isIpl"], first["seasonYear"])
        self.logistic.fit(design, first["battingTeamWon"])
        return self

    def designMatrix(self, runs, wickets, ballsLeft, isIpl, seasonYear):
        ballsLeft = np.maximum(np.asarray(ballsLeft, dtype=float), 0.0)
        wicketsInHand = WICKETS_PER_INNINGS - np.asarray(wickets)
        projected = np.asarray(runs) + self.resource.expectedRemaining(ballsLeft, wicketsInHand, isIpl, seasonYear)
        fractionLeft = np.where(wicketsInHand > 0, ballsLeft / BALLS_PER_INNINGS, 0.0)
        return np.column_stack([projected, projected * fractionLeft, fractionLeft,
                                np.asarray(isIpl, dtype=float), np.asarray(seasonYear, dtype=float)])

    def predict(self, runs, wickets, ballsLeft, isIpl, seasonYear):
        return self.logistic.predict_proba(self.designMatrix(runs, wickets, ballsLeft, isIpl, seasonYear))[:, 1]


class ChaseModel:
    """Win probability chasing: monotone gradient boosting on runs required, balls left, wickets in hand."""

    def __init__(self):
        self.classifier = HistGradientBoostingClassifier(
            max_iter=WIN_MODEL_ITERATIONS, learning_rate=WIN_MODEL_LEARNING_RATE,
            min_samples_leaf=WIN_MODEL_MIN_LEAF, monotonic_cst=CHASE_MONOTONE, random_state=RANDOM_SEED)

    def fit(self, states):
        chase = states[(states["innings"] == 2) & states["hasResult"]]
        self.classifier.fit(chase[CHASE_FEATURES], chase["battingTeamWon"])
        return self

    def predict(self, runsRequired, ballsLeft, wicketsInHand, isIpl):
        features = pd.DataFrame({"runsRequired": runsRequired, "ballsLeft": ballsLeft,
                                 "wicketsInHand": wicketsInHand, "isIpl": isIpl})
        live = ((features["runsRequired"] > 0) & (features["ballsLeft"] > 0)
                & (features["wicketsInHand"] > 0)).to_numpy()
        lostValue = np.where(features["runsRequired"] == 1, TIED_CHASE_PROBABILITY, 0.0)
        result = np.where(features["runsRequired"] <= 0, 1.0, lostValue)
        if live.any():
            result[live] = self.classifier.predict_proba(features[live])[:, 1]
        return result


class WinProbabilityModel:
    """Batting-side win probability from any (possibly terminal) match state."""

    def __init__(self):
        self.firstInnings = FirstInningsModel()
        self.chase = ChaseModel()

    def fit(self, states):
        self.firstInnings.fit(states)
        self.chase.fit(states)
        return self

    def predictState(self, innings, runs, wickets, ballsLeft, target, isIpl, seasonYear):
        first = self.firstInnings.predict(runs, wickets, ballsLeft, isIpl, seasonYear)
        chase = self.chase.predict(np.asarray(target) - np.asarray(runs), ballsLeft,
                                   WICKETS_PER_INNINGS - np.asarray(wickets), isIpl)
        return np.where(np.asarray(innings) == 1, first, chase)

    def predictStates(self, states):
        return self.predictState(states["innings"], states["runsBefore"], states["wicketsBefore"],
                                 states["ballsLeft"], states["target"].fillna(0), states["isIpl"],
                                 states["seasonYear"])


def crossValidateWinModels(states):
    """Match-grouped out-of-fold accuracy, so no match informs its own prediction."""
    labelled = states[states["hasResult"]].reset_index(drop=True)
    predicted = np.zeros(len(labelled))
    folds = GroupKFold(n_splits=CROSS_VALIDATION_FOLDS)
    for trainIndex, testIndex in folds.split(labelled, groups=labelled["match_id"]):
        model = WinProbabilityModel().fit(labelled.iloc[trainIndex])
        predicted[testIndex] = model.predictStates(labelled.iloc[testIndex])
    metrics, calibration = [], []
    for innings in (1, 2):
        mask = (labelled["innings"] == innings).to_numpy()
        actual = labelled.loc[mask, "battingTeamWon"].to_numpy()
        metrics.append(scoreProbabilities(innings, labelled[mask], actual, predicted[mask]))
        calibration.append(calibrationTable(actual, predicted[mask]).assign(innings=innings))
    return pd.DataFrame(metrics), pd.concat(calibration, ignore_index=True)


def scoreProbabilities(innings, subset, actual, predicted):
    return {"innings": innings, "balls": len(subset), "matches": subset["match_id"].nunique(),
            "brier": brier_score_loss(actual, predicted), "logLoss": log_loss(actual, predicted),
            "auc": roc_auc_score(actual, predicted), "baseRate": actual.mean()}


def calibrationTable(actual, predicted):
    bins = np.minimum((predicted * CALIBRATION_BINS).astype(int), CALIBRATION_BINS - 1)
    table = pd.DataFrame({"bin": bins, "predicted": predicted, "actual": actual})
    return table.groupby("bin").agg(predicted=("predicted", "mean"), actual=("actual", "mean"),
                                    balls=("actual", "size")).reset_index()
