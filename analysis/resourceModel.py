import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from pipelineConfig import (
    OUTCOME_MODEL_ITERATIONS,
    OUTCOME_MODEL_LEARNING_RATE,
    RANDOM_SEED,
    RESOURCE_MODEL_MIN_LEAF,
)

RESOURCE_FEATURES = ["ballsLeft", "wicketsInHand", "isIpl", "seasonYear"]
RESOURCE_MONOTONE = [1, 1, 0, 0]


class ResourceModel:
    """Expected further runs in a first innings from (balls left, wickets in hand): a data-fitted DLS-style table."""

    def __init__(self):
        self.regressor = HistGradientBoostingRegressor(
            max_iter=OUTCOME_MODEL_ITERATIONS, learning_rate=OUTCOME_MODEL_LEARNING_RATE,
            min_samples_leaf=RESOURCE_MODEL_MIN_LEAF, monotonic_cst=RESOURCE_MONOTONE, random_state=RANDOM_SEED)

    def fit(self, states):
        first = states[(states["innings"] == 1) & states["hasResult"]]
        remainingRuns = first["inningsTotal"] - first["runsBefore"]
        self.regressor.fit(first[RESOURCE_FEATURES], remainingRuns)
        return self

    def expectedRemaining(self, ballsLeft, wicketsInHand, isIpl, seasonYear):
        features = pd.DataFrame({"ballsLeft": ballsLeft, "wicketsInHand": wicketsInHand,
                                 "isIpl": isIpl, "seasonYear": seasonYear})
        live = ((features["ballsLeft"] > 0) & (features["wicketsInHand"] > 0)).to_numpy()
        result = np.zeros(len(features))
        if live.any():
            result[live] = self.regressor.predict(features[live])
        return result

    def wicketCost(self, states):
        """Runs of batting resource lost if a wicket falls on this delivery."""
        ballsAfter = states["ballsLeft"] - 1
        kept = self.expectedRemaining(ballsAfter, states["wicketsInHand"], states["isIpl"], states["seasonYear"])
        lost = self.expectedRemaining(ballsAfter, states["wicketsInHand"] - 1, states["isIpl"], states["seasonYear"])
        return np.maximum(kept - lost, 0.0)
