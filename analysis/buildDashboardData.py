"""Stage 7: export player-level aggregates for the web dashboard. No ball-by-ball records leave the pipeline."""
import json
import shutil

import pandas as pd

from buildBallImpacts import BATTER_BALLS_FILE, BOWLER_BALLS_FILE
from buildPressureStates import STATES_FILE
from buildProfiles import LATEST_IPL, batterProfiles, bowlerProfiles
from buildReport import REPORT_PDF
from dataLoader import loadSquadMapping
from pipelineConfig import ANALYSIS_DIR, BOOTSTRAP_ROUNDS, OUTPUT_DIR, PRESSURE_QUANTILE, TOP_LIST_SIZE
from reportCharts import chaseHeatmapGrid
from reportFacts import ROYALS_RECORD_FROM_SEASON, gatherFacts

DASHBOARD_DIR = ANALYSIS_DIR.parent / "dashboard"
DATA_FILE = DASHBOARD_DIR / "dashboardData.js"
REPORT_COPY = DASHBOARD_DIR / "methodologyReport.pdf"
PROFILE_BUILDERS = {"batter": (batterProfiles, BATTER_BALLS_FILE), "bowler": (bowlerProfiles, BOWLER_BALLS_FILE)}
SHARED_COLUMNS = ["playerId", "playerName", "rank", "finalRank", "rating", "posteriorSd", "rawPressureImpact",
                  "rawBaselineImpact", "dipProbability", "provenUnderPressure", "passesDipGate", "rankLow",
                  "rankMedian", "rankHigh", "topListProbability", "rawOutingRate", "ballsPressure", "ballsBaseline",
                  "dotSharePressure", "boundarySharePressure", "matches", "lastMatch"]
ROLE_COLUMNS = {
    "batter": ["strikeRatePressure", "averagePressure", "strikeRateBaseline", "runsPressure", "outsPressure"],
    "bowler": ["economyPressure", "wicketsPressure", "economyBaseline", "pace_or_spin"],
}
DATE_FORMAT = "%d %b %Y"


def main():
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    facts = gatherFacts()
    states = pd.read_pickle(STATES_FILE)
    payload = {
        "summary": summaryFacts(facts),
        "heatmap": heatmapPayload(states),
        "calibration": records(pd.read_csv(OUTPUT_DIR / "winModelCalibration.csv")),
        "roles": {role: rolePayload(role, facts[role]) for role in PROFILE_BUILDERS},
        "royals": royalsPayload(facts),
    }
    script = "export const dashboardData = " + json.dumps(payload, indent=1, allow_nan=False) + ";\n"
    DATA_FILE.write_text(script, encoding="utf-8")
    shutil.copyfile(REPORT_PDF, REPORT_COPY)
    print(f"dashboard data written to {DATA_FILE} ({DATA_FILE.stat().st_size // 1024} KB)")


def records(frame):
    """JSON-safe rows: missing values become null, timestamps become readable dates."""
    frame = frame.copy()
    for column in frame.select_dtypes(include="datetime").columns:
        frame[column] = frame[column].dt.strftime(DATE_FORMAT)
    return json.loads(frame.to_json(orient="records"))


def summaryFacts(facts):
    data, pressure = facts["data"], facts["pressure"]
    comparison = pressure["comparison"].rename(index={True: "pressure", False: "ordinary"})
    return {
        "usedMatches": data["usedMatches"], "usedBalls": data["usedBalls"],
        "usedIplMatches": data["usedIplMatches"], "usedInternationalMatches": data["usedInternationalMatches"],
        "firstDate": data["firstDate"].strftime(DATE_FORMAT), "lastDate": data["lastDate"].strftime(DATE_FORMAT),
        "resultsChecked": data["resultsChecked"], "resultMismatches": data["resultMismatches"],
        "pressureBalls": pressure["pressureBalls"], "pressureShare": 1 - PRESSURE_QUANTILE,
        "pressureThreshold": pressure["threshold"], "chaseShareOfPressure": pressure["chaseShareOfPressure"],
        "comparison": json.loads(comparison.to_json(orient="index")),
        "winMetrics": json.loads(facts["winMetrics"].to_json(orient="index")),
        "topListSize": TOP_LIST_SIZE, "latestIpl": LATEST_IPL,
        "bootstrapRounds": BOOTSTRAP_ROUNDS, "royalsFromSeason": ROYALS_RECORD_FROM_SEASON,
    }


def heatmapPayload(states):
    share = chaseHeatmapGrid(states, "mean")
    balls = chaseHeatmapGrid(states, "size")
    return {"rateLabels": list(share.index), "ballLabels": list(share.columns),
            "pressureShare": share.round(4).to_numpy().tolist(), "balls": balls.to_numpy().tolist()}


def rolePayload(role, roleFacts):
    builder, ballsFile = PROFILE_BUILDERS[role]
    ratings = roleFacts["ratings"].set_index("playerId")
    squads = loadSquadMapping()
    latestTeams = squads[squads["comp_name"] == LATEST_IPL].set_index("player_id")["team_name"]
    profiles = builder(ratings, pd.read_pickle(ballsFile), latestTeams, selector=lambda table: table)
    players = roleFacts["ratings"][SHARED_COLUMNS + ROLE_COLUMNS[role]].merge(
        profiles.drop(columns=["playerName", "finalRank"]), left_on="playerId", right_index=True, how="left")
    players["lastMatch"] = pd.to_datetime(players["lastMatch"])
    return {
        "players": records(players),
        "splitHalf": json.loads(roleFacts["splitHalf"].to_json(orient="index")),
        "heldOut": json.loads(roleFacts["heldOut"].to_json(orient="index")),
        "sensitivity": records(roleFacts["sensitivity"]),
        "liftSignalVariance": roleFacts["shrinkage"]["liftSignalVarianceUntruncated"],
    }


def royalsPayload(facts):
    record = facts["royalsRecord"]
    rows = []
    for (discipline, phase), row in record.iterrows():
        royals, others = row[("impactPer100", "Royals")], row[("impactPer100", "Other teams")]
        rows.append({"discipline": discipline, "phase": phase, "royalsBalls": int(row[("balls", "Royals")]),
                     "royals": royals, "others": others, "gap": royals - others})
    squad = facts["royalsSquad"]
    rated = squad[squad["batting_rank"].notna() | squad["bowling_rank"].notna()]
    return {"record": rows, "squad": records(rated), "unratedSquadMembers": len(squad) - len(rated)}


if __name__ == "__main__":
    main()
