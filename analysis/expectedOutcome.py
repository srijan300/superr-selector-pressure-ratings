import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from pipelineConfig import (
    CROSS_VALIDATION_FOLDS,
    OUTCOME_MODEL_ITERATIONS,
    OUTCOME_MODEL_LEARNING_RATE,
    OUTCOME_MODEL_MIN_LEAF,
    RANDOM_SEED,
)

SITUATION_FEATURES = ["innings", "overNumber", "ballsLeft", "wicketsBefore", "currentRunRate",
                      "requiredRunRate", "isIpl", "seasonYear", "strikerBallsFaced"]
BATTER_VIEW_FEATURES = SITUATION_FEATURES + ["isSpin", "opponentTeam"]
BOWLER_VIEW_FEATURES = SITUATION_FEATURES + ["batting_order", "isLeftHander", "opponentTeam"]
CATEGORICAL_FEATURES = ["opponentTeam"]
SPIN_LABEL = "Spin"
LEFT_HANDER_LABEL = "LHB"


def addBatterExpectations(states):
    """Out-of-fold expected runs and dismissal chance for the striker, given situation and opposition."""
    view = states[~states["isWide"]].copy()
    view["isSpin"] = view["pace_or_spin"] == SPIN_LABEL
    view["opponentTeam"] = view["bowling_team_id"].astype("category")
    view["expectedRuns"] = outOfFold(view, BATTER_VIEW_FEATURES, view["runs"], isClassifier=False)
    view["expectedOut"] = outOfFold(view, BATTER_VIEW_FEATURES, view["strikerOut"], isClassifier=True)
    return view


def addBowlerExpectations(states):
    """Out-of-fold expected runs conceded and wicket chance for the bowler, given situation and opposition."""
    view = states.copy()
    view["isLeftHander"] = view["batting_type"] == LEFT_HANDER_LABEL
    view["opponentTeam"] = view["batting_team_id"].astype("category")
    view["expectedRuns"] = outOfFold(view, BOWLER_VIEW_FEATURES, view["bowlerRuns"], isClassifier=False)
    view["expectedWicket"] = outOfFold(view, BOWLER_VIEW_FEATURES, view["bowlerWicket"], isClassifier=True)
    return view


def outOfFold(view, features, target, isClassifier):
    predicted = np.zeros(len(view))
    folds = GroupKFold(n_splits=CROSS_VALIDATION_FOLDS)
    for trainIndex, testIndex in folds.split(view, groups=view["match_id"]):
        model = newOutcomeModel(isClassifier)
        model.fit(view.iloc[trainIndex][features], target.iloc[trainIndex])
        testRows = view.iloc[testIndex][features]
        predicted[testIndex] = model.predict_proba(testRows)[:, 1] if isClassifier else model.predict(testRows)
    return predicted


def newOutcomeModel(isClassifier):
    modelClass = HistGradientBoostingClassifier if isClassifier else HistGradientBoostingRegressor
    return modelClass(max_iter=OUTCOME_MODEL_ITERATIONS, learning_rate=OUTCOME_MODEL_LEARNING_RATE,
                      min_samples_leaf=OUTCOME_MODEL_MIN_LEAF, categorical_features=CATEGORICAL_FEATURES,
                      random_state=RANDOM_SEED)


def chaseCappedWicketCost(view, resourceModel):
    """A wicket cannot cost more runs than the chase still needs."""
    cost = resourceModel.wicketCost(view)
    return np.where(view["innings"] == 2, np.minimum(cost, view["runsRequired"].clip(lower=0)), cost)


def batterImpact(view, resourceModel):
    """Runs added above expectation, net of the resource cost of being dismissed more often than expected."""
    wicketCost = chaseCappedWicketCost(view, resourceModel)
    runsAbove = view["runs"] - view["expectedRuns"]
    dismissalsAbove = view["strikerOut"].astype(float) - view["expectedOut"]
    return pd.DataFrame({"runImpact": runsAbove, "wicketImpact": -wicketCost * dismissalsAbove,
                         "impact": runsAbove - wicketCost * dismissalsAbove}, index=view.index)


def bowlerImpact(view, resourceModel):
    """Runs saved below expectation, plus the resource value of wickets taken above expectation."""
    wicketCost = chaseCappedWicketCost(view, resourceModel)
    runsSaved = view["expectedRuns"] - view["bowlerRuns"]
    wicketsAbove = view["bowlerWicket"].astype(float) - view["expectedWicket"]
    return pd.DataFrame({"runImpact": runsSaved, "wicketImpact": wicketCost * wicketsAbove,
                         "impact": runsSaved + wicketCost * wicketsAbove}, index=view.index)
