"""Stage 4: role profiles for the listed players and Rajasthan Royals' own pressure record."""
import pandas as pd

from buildBallImpacts import BATTER_BALLS_FILE, BOWLER_BALLS_FILE
from buildRatings import ratingFile
from dataLoader import loadSquadMapping
from pipelineConfig import BALLS_PER_OVER, OUTPUT_DIR, PER_HUNDRED, TOP_LIST_SIZE

ROYALS_TEAM_NAME = "Rajasthan Royals"
LATEST_IPL = "IPL 2026"
RESERVE_COUNT = 5
PHASES = ("powerplay", "middle", "death")
BOWLING_KINDS = ("Pace", "Spin")


def main():
    squads = loadSquadMapping()
    latestTeams = squads[squads["comp_name"] == LATEST_IPL].set_index("player_id")["team_name"]
    batterBalls = pd.read_pickle(BATTER_BALLS_FILE)
    bowlerBalls = pd.read_pickle(BOWLER_BALLS_FILE)
    batters = pd.read_csv(ratingFile("batter"), index_col="playerId")
    bowlers = pd.read_csv(ratingFile("bowler"), index_col="playerId")
    batterProfiles(batters, batterBalls, latestTeams).to_csv(OUTPUT_DIR / "batterProfiles.csv")
    bowlerProfiles(bowlers, bowlerBalls, latestTeams).to_csv(OUTPUT_DIR / "bowlerProfiles.csv")
    royalsSquad(latestTeams, squads, batters, bowlers).to_csv(OUTPUT_DIR / "royalsSquad.csv")
    royalsId = squads.loc[squads["team_name"] == ROYALS_TEAM_NAME, "team_id"].iloc[0]
    royalsRecord(batterBalls, bowlerBalls, royalsId).to_csv(OUTPUT_DIR / "royalsPressureRecord.csv", index=False)


def shortlist(ratings):
    listed = ratings[ratings["finalRank"] <= TOP_LIST_SIZE + RESERVE_COUNT]
    return listed.sort_values("finalRank")


def batterProfiles(ratings, balls, latestTeams, selector=shortlist):
    listed = selector(ratings)
    pressure = balls[balls["isPressure"] & balls["playerId"].isin(listed.index)]
    profile = listed[["playerName", "finalRank"]].copy()
    profile["latestIplTeam"] = latestTeams.reindex(profile.index)
    profile["typicalPosition"] = pressure.groupby("playerId")["batting_order"].median()
    profile = profile.join(shareByPhase(pressure))
    for kind in BOWLING_KINDS:
        subset = pressure[pressure["pace_or_spin"] == kind].groupby("playerId")
        profile[f"strikeRateVs{kind}"] = subset["runs"].sum() / subset["isLegal"].sum() * PER_HUNDRED
    profile["pressureMatches"] = pressure.groupby("playerId")["match_id"].nunique()
    return profile


def bowlerProfiles(ratings, balls, latestTeams, selector=shortlist):
    listed = selector(ratings)
    pressure = balls[balls["isPressure"] & balls["playerId"].isin(listed.index)]
    profile = listed[["playerName", "finalRank"]].copy()
    profile["latestIplTeam"] = latestTeams.reindex(profile.index)
    profile["bowlingType"] = pressure.groupby("playerId")["bowling_type"].agg(lambda kinds: kinds.mode().iloc[0])
    profile = profile.join(shareByPhase(pressure))
    for phase in PHASES:
        subset = pressure[pressure["phase"] == phase].groupby("playerId")
        profile[f"{phase}Economy"] = subset["bowlerRuns"].sum() / subset["isLegal"].sum() * BALLS_PER_OVER
    return profile


def shareByPhase(pressure):
    counts = pd.crosstab(pressure["playerId"], pressure["phase"])
    shares = counts.div(counts.sum(axis=1), axis=0).reindex(columns=PHASES, fill_value=0.0)
    return shares.add_suffix("Share")


def royalsSquad(latestTeams, squads, batters, bowlers):
    """Where each current Royals player sits in the two rankings, if they have enough pressure evidence."""
    royalsIds = latestTeams[latestTeams == ROYALS_TEAM_NAME].index
    names = squads.drop_duplicates("player_id").set_index("player_id")["player_name"]
    squad = pd.DataFrame({"playerName": names.reindex(royalsIds)}, index=royalsIds)
    columns = ["rank", "finalRank", "rating", "rawPressureImpact", "pressureBalls"]
    squad = squad.join(batters[columns].add_prefix("batting_")).join(bowlers[columns].add_prefix("bowling_"))
    return squad.sort_values(["batting_rank", "bowling_rank"])


def royalsRecord(batterBalls, bowlerBalls, royalsId):
    """Royals' impact per 100 pressure balls in the IPL, by season and phase, next to the other nine teams."""
    frames = []
    views = {"batting": (batterBalls, "batting_team_id"), "bowling": (bowlerBalls, "bowling_team_id")}
    for discipline, (balls, teamColumn) in views.items():
        pressure = balls[balls["isIpl"] & balls["isPressure"]].copy()
        pressure["side"] = (pressure[teamColumn] == royalsId).map({True: "Royals", False: "Other teams"})
        grouped = pressure.groupby(["seasonYear", "phase", "side"]).agg(
            balls=("impact", "size"), impactPer100=("impact", lambda values: values.mean() * PER_HUNDRED))
        frames.append(grouped.reset_index().assign(discipline=discipline))
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    main()
