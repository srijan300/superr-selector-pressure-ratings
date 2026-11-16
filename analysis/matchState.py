import numpy as np

from pipelineConfig import (
    BALLS_PER_INNINGS,
    BALLS_PER_OVER,
    BOWLER_DISMISSALS,
    MIDDLE_LAST_OVER,
    NO_BALL_TYPES,
    POWERPLAY_LAST_OVER,
    WICKETS_PER_INNINGS,
    WIDE_TYPES,
)

MATCH_COLUMNS = ["match_id", "match_date", "isIpl", "isInternational", "season", "comp_id",
                 "win_team_id", "hasResult", "knock_out"]
PHASE_LABELS = ("powerplay", "middle", "death")


def buildBallStates(balls, matches):
    """Attach the pre-delivery match state to every regulation ball of non-revised matches."""
    usable = matches[~matches["isRainRevised"]]
    frame = balls.merge(usable[MATCH_COLUMNS], on="match_id", how="inner", validate="many_to_one")
    frame["seasonYear"] = frame["match_date"].dt.year
    frame = addDeliveryFlags(frame)
    frame = addRunningTotals(frame)
    frame = addChaseContext(frame)
    frame = addBatterContext(frame)
    return frame


def addDeliveryFlags(frame):
    frame["isWide"] = frame["extras_type"].isin(WIDE_TYPES)
    frame["isNoBall"] = frame["extras_type"].isin(NO_BALL_TYPES)
    frame["isLegal"] = ~(frame["isWide"] | frame["isNoBall"])
    frame["totalRuns"] = frame["runs"] + frame["extras1_runs"] + frame["extras_2_runs"]
    bowlerExtras = np.where(frame["isWide"] | frame["isNoBall"], frame["extras1_runs"], 0)
    frame["bowlerRuns"] = frame["runs"] + bowlerExtras
    dismissed = frame["dismissed_player_id"].fillna(frame["striker_id"])
    frame["strikerOut"] = frame["is_wicket"] & (dismissed == frame["striker_id"])
    frame["bowlerWicket"] = frame["is_wicket"] & frame["dismissal_type"].isin(BOWLER_DISMISSALS)
    return frame


def addRunningTotals(frame):
    grouped = frame.groupby(["match_id", "innings"], sort=False)
    frame["runsBefore"] = grouped["totalRuns"].cumsum() - frame["totalRuns"]
    frame["wicketsBefore"] = grouped["is_wicket"].cumsum() - frame["is_wicket"].astype(int)
    frame["legalBallsBefore"] = grouped["isLegal"].cumsum() - frame["isLegal"].astype(int)
    frame["ballsLeft"] = BALLS_PER_INNINGS - frame["legalBallsBefore"]
    frame["wicketsInHand"] = WICKETS_PER_INNINGS - frame["wicketsBefore"]
    frame["overNumber"] = frame["legalBallsBefore"] // BALLS_PER_OVER + 1
    frame["phase"] = np.select(
        [frame["overNumber"] <= POWERPLAY_LAST_OVER, frame["overNumber"] <= MIDDLE_LAST_OVER],
        PHASE_LABELS[:2], default=PHASE_LABELS[2])
    frame["inningsTotal"] = grouped["totalRuns"].transform("sum")
    oversBowled = np.maximum(frame["legalBallsBefore"], 1) / BALLS_PER_OVER
    frame["currentRunRate"] = np.where(frame["legalBallsBefore"] > 0, frame["runsBefore"] / oversBowled, 0.0)
    return frame[frame["ballsLeft"] > 0].copy()


def addChaseContext(frame):
    firstTotals = frame[frame["innings"] == 1].groupby("match_id")["inningsTotal"].first()
    frame["target"] = frame["match_id"].map(firstTotals) + 1
    isChase = frame["innings"] == 2
    frame["runsRequired"] = np.where(isChase, frame["target"] - frame["runsBefore"], np.nan)
    oversLeft = frame["ballsLeft"] / BALLS_PER_OVER
    frame["requiredRunRate"] = np.where(isChase, frame["runsRequired"] / oversLeft, np.nan)
    frame["battingTeamWon"] = np.where(
        frame["hasResult"], (frame["win_team_id"] == frame["batting_team_id"]).astype(float), np.nan)
    return frame


def addBatterContext(frame):
    """Balls already faced by the striker in this innings: a proxy for how settled they are."""
    faced = (~frame["isWide"]).astype(int)
    grouped = faced.groupby([frame["match_id"], frame["innings"], frame["striker_id"]], sort=False)
    frame["strikerBallsFaced"] = grouped.cumsum() - faced
    return frame
