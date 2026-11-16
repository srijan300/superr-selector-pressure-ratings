import pandas as pd

from pipelineConfig import DATA_DIR, IPL_NAME_PREFIX, REGULATION_INNINGS

RAIN_RULE_PATTERN = "D/L|DLS"


def loadMatches():
    matches = pd.read_csv(DATA_DIR / "matches.csv", parse_dates=["match_date"])
    competitions = pd.read_csv(DATA_DIR / "competitions.csv")
    matches = matches.merge(competitions, on="comp_id", how="left", validate="many_to_one")
    matches["isIpl"] = matches["comp_name"].str.startswith(IPL_NAME_PREFIX)
    matches["isInternational"] = matches["match_format"] == "T20I"
    revisedColumns = ["first_inn_revised_overs", "second_inn_revised_overs", "revised_target"]
    statedRainRule = matches["result"].str.contains(RAIN_RULE_PATTERN, case=False, na=False)
    matches["isRainRevised"] = matches[revisedColumns].notna().any(axis=1) | statedRainRule
    matches["hasResult"] = matches["win_team_id"].notna()
    return matches


def loadBalls():
    balls = pd.read_csv(DATA_DIR / "ball_by_ball.csv", low_memory=False)
    balls = balls[balls["innings"].isin(REGULATION_INNINGS)].copy()
    balls = balls.sort_values(["match_id", "innings", "innings_ball_num"], kind="stable")
    return balls.reset_index(drop=True)


def loadPlayerNames(balls):
    strikers = balls[["striker_id", "striker_name"]].set_axis(["playerId", "playerName"], axis=1)
    bowlers = balls[["bowler_id", "bowler_name"]].set_axis(["playerId", "playerName"], axis=1)
    names = pd.concat([strikers, bowlers]).drop_duplicates("playerId")
    return names.set_index("playerId")["playerName"]


def loadSquadMapping():
    return pd.read_csv(DATA_DIR / "competition_team_player_mapping.csv")
