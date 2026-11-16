"""Stage 1: rebuild match states, fit win probability, attach leverage and the pressure flag."""
from dataLoader import loadBalls, loadMatches
from matchState import buildBallStates
from pipelineConfig import OUTPUT_DIR
from pressureIndex import addWinProbabilityAndLeverage, flagPressure, outcomeProbabilities
from winProbability import WinProbabilityModel, crossValidateWinModels

STATES_FILE = OUTPUT_DIR / "ballStates.pkl"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    matches = loadMatches()
    states = buildBallStates(loadBalls(), matches)
    metrics, calibration = crossValidateWinModels(states)
    metrics.to_csv(OUTPUT_DIR / "winModelMetrics.csv", index=False)
    calibration.to_csv(OUTPUT_DIR / "winModelCalibration.csv", index=False)
    winModel = WinProbabilityModel().fit(states)
    states = addWinProbabilityAndLeverage(states, winModel)
    states["isPressure"] = flagPressure(states)
    outcomeProbabilities(states).to_csv(OUTPUT_DIR / "outcomeProbabilities.csv")
    states.to_pickle(STATES_FILE)
    print(metrics.to_string(index=False))
    print(f"states: {len(states)} balls, {states['match_id'].nunique()} matches")
    print(f"pressure balls: {int(states['isPressure'].sum())}")


if __name__ == "__main__":
    main()
