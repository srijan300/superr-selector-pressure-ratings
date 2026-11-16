"""Stage 2: per-ball impact above expectation for the striker and the bowler."""
import pandas as pd

from buildPressureStates import STATES_FILE
from expectedOutcome import addBatterExpectations, addBowlerExpectations, batterImpact, bowlerImpact
from pipelineConfig import OUTPUT_DIR
from resourceModel import ResourceModel

BATTER_BALLS_FILE = OUTPUT_DIR / "batterBalls.pkl"
BOWLER_BALLS_FILE = OUTPUT_DIR / "bowlerBalls.pkl"
KEPT_COLUMNS = ["match_id", "match_date", "innings", "phase", "isIpl", "isInternational", "seasonYear",
                "batting_team_id", "bowling_team_id",
                "knock_out", "isLegal", "isPressure", "leverage", "wpBefore", "wpAfter", "ballsLeft",
                "wicketsBefore", "requiredRunRate", "expectedRuns", "runImpact", "wicketImpact", "impact"]
BATTER_COLUMNS = ["striker_id", "runs", "strikerOut", "expectedOut", "pace_or_spin", "batting_order"]
BOWLER_COLUMNS = ["bowler_id", "bowlerRuns", "bowlerWicket", "expectedWicket", "pace_or_spin", "bowling_type"]


def main():
    states = pd.read_pickle(STATES_FILE)
    resourceModel = ResourceModel().fit(states)
    batterView = addBatterExpectations(states)
    batterView = batterView.join(batterImpact(batterView, resourceModel))
    bowlerView = addBowlerExpectations(states)
    bowlerView = bowlerView.join(bowlerImpact(bowlerView, resourceModel))
    batterView[KEPT_COLUMNS + BATTER_COLUMNS].rename(columns={"striker_id": "playerId"}).to_pickle(BATTER_BALLS_FILE)
    bowlerView[KEPT_COLUMNS + BOWLER_COLUMNS].rename(columns={"bowler_id": "playerId"}).to_pickle(BOWLER_BALLS_FILE)
    summariseResiduals("batter", batterView).to_csv(OUTPUT_DIR / "batterModelResiduals.csv")
    summariseResiduals("bowler", bowlerView).to_csv(OUTPUT_DIR / "bowlerModelResiduals.csv")


def summariseResiduals(label, view):
    """Mean impact should be near zero in every slice if expectations are well calibrated."""
    table = view.groupby(["innings", "phase", "isPressure"]).agg(
        balls=("impact", "size"), expectedRuns=("expectedRuns", "mean"),
        runImpact=("runImpact", "mean"), wicketImpact=("wicketImpact", "mean"), impact=("impact", "mean"))
    print(label)
    print(table.round(4).to_string())
    return table


if __name__ == "__main__":
    main()
