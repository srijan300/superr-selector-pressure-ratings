from buildProfiles import LATEST_IPL, PHASES, ROYALS_TEAM_NAME
from reportFacts import ROYALS_RECORD_FROM_SEASON
from reportTables import bulletList, htmlTable, number, paragraph, percent, section, signed, text

DISCIPLINES = ("batting", "bowling")
PHASE_NAMES = {"powerplay": "powerplay", "middle": "middle overs", "death": "death overs"}
NO_IPL_TEAM = f"not in an {LATEST_IPL} squad"
DEATH_SPECIALISTS_SHOWN = 3


def royalsSection(facts):
    record = facts["royalsRecord"]
    gaps = phaseGaps(record)
    weakest = {discipline: gaps[discipline].idxmin() for discipline in DISCIPLINES}
    intro = paragraph(
        f"The same per-ball impact, summed for Rajasthan Royals on IPL pressure balls from "
        f"{ROYALS_RECORD_FROM_SEASON} to the latest season, shows where reinforcements matter most. Samples "
        "per phase are a few hundred balls, so read these as direction, not precise size.")
    reading = paragraph(
        f"Royals' largest shortfall against the other nine teams is in the "
        f"<b>{PHASE_NAMES[weakest['batting']]} with the bat</b> ({signed(gaps['batting'][weakest['batting']])} per 100 "
        f"balls) and the <b>{PHASE_NAMES[weakest['bowling']]} with the ball</b> "
        f"({signed(gaps['bowling'][weakest['bowling']])}).")
    caveat = paragraph(
        "The pack does not say who will be retained or released, so the lists rank ability under pressure, "
        "not availability. The notes below say what each player would add if obtainable.")
    return section("8. What this means for Rajasthan Royals", intro, recordTable(record, gaps), reading,
                   squadTable(facts), deathSpecialists(facts), caveat,
                   "<h3>Batters</h3>" + bulletList(batterNotes(facts, record, weakest["batting"])),
                   "<h3>Bowlers</h3>" + bulletList(bowlerNotes(facts, record, weakest["bowling"])))


def deathSpecialists(facts):
    """Listed players who do the largest share of their pressure work in the death overs."""
    parts = []
    for role, label in (("batter", "batters"), ("bowler", "bowlers")):
        listedIds = facts[role]["listed"]["playerId"]
        profiles = facts[role]["profiles"].loc[listedIds].sort_values("deathShare", ascending=False)
        names = [f"{text(row.playerName)} ({percent(row.deathShare)} of pressure balls at the death)"
                 for row in profiles.head(DEATH_SPECIALISTS_SHOWN).itertuples()]
        parts.append(f"among the listed {label}, " + ", ".join(names))
    return paragraph("The listed players with the largest share of their pressure balls at the death are: "
                     + "; ".join(parts) + ".")


def phaseGaps(record):
    impact = record["impactPer100"]
    return {discipline: (impact.loc[discipline, "Royals"] - impact.loc[discipline, "Other teams"])
            for discipline in DISCIPLINES}


def recordTable(record, gaps):
    rows = []
    for discipline in DISCIPLINES:
        for phase in PHASES:
            row = record.loc[(discipline, phase)]
            rows.append([discipline.capitalize(), PHASE_NAMES[phase], number(row[("balls", "Royals")], 0),
                         signed(row[("impactPer100", "Royals")]), signed(row[("impactPer100", "Other teams")]),
                         signed(gaps[discipline][phase])])
    headers = ["Discipline", "Phase", "Royals pressure balls", "Royals impact / 100", "Other teams", "Gap"]
    return htmlTable(headers, rows, textColumns=2)


def squadTable(facts):
    squad = facts["royalsSquad"]
    rated = squad[squad["batting_rank"].notna() | squad["bowling_rank"].notna()]
    rows = []
    for row in rated.itertuples():
        rows.append([text(row.playerName), rankText(row.batting_rank, len(facts["batter"]["ratings"])),
                     signed(row.batting_rawPressureImpact), rankText(row.bowling_rank, len(facts["bowler"]["ratings"])),
                     signed(row.bowling_rawPressureImpact)])
    unrated = len(squad) - len(rated)
    headers = [f"Royals squad, {LATEST_IPL}", "Batting rank", "Batting pressure impact", "Bowling rank",
               "Bowling pressure impact"]
    note = paragraph(f"The other {unrated} squad members have too few pressure balls in the pack to rate.")
    return htmlTable(headers, rows) + note


def rankText(rank, eligibleCount):
    if rank != rank:
        return "-"
    return f"{int(rank)} of {eligibleCount}"


def dominantPhase(profile):
    shares = {phase: profile[f"{phase}Share"] for phase in PHASES}
    phase = max(shares, key=shares.get)
    return phase, shares[phase]


def fitSentence(team, discipline, phase, record, weakestPhase):
    if team == ROYALS_TEAM_NAME:
        return f"Already a Royal in {LATEST_IPL}: the task is to keep this player, not to buy."
    gap = phaseGaps(record)[discipline][phase]
    sentence = f"Royals' gap to other teams in this phase: {signed(gap)} per 100 balls."
    if phase == weakestPhase:
        return sentence + " This is their biggest gap, so a direct fix."
    return sentence


def batterNotes(facts, record, weakestPhase):
    notes = []
    profiles = facts["batter"]["profiles"]
    for row in facts["batter"]["listed"].itertuples():
        profile = profiles.loc[row.playerId]
        team = profile["latestIplTeam"]
        phase, share = dominantPhase(profile)
        notes.append(
            f"<b>{int(row.finalRank)}. {text(row.playerName)}</b> ({text(team) if team == team else NO_IPL_TEAM}; "
            f"usually bats at {number(profile['typicalPosition'], 0)}). {percent(share)} of pressure balls faced are "
            f"in the {PHASE_NAMES[phase]}; pressure strike rate {number(row.strikeRatePressure, 0)} at an average of "
            f"{number(row.averagePressure)}, with {number(profile['strikeRateVsPace'], 0)} against pace and "
            f"{number(profile['strikeRateVsSpin'], 0)} against spin. "
            + fitSentence(team, "batting", phase, record, weakestPhase))
    return notes


def bowlerNotes(facts, record, weakestPhase):
    notes = []
    profiles = facts["bowler"]["profiles"]
    for row in facts["bowler"]["listed"].itertuples():
        profile = profiles.loc[row.playerId]
        team = profile["latestIplTeam"]
        phase, share = dominantPhase(profile)
        notes.append(
            f"<b>{int(row.finalRank)}. {text(row.playerName)}</b> ({text(profile['bowlingType']).lower()}; "
            f"{text(team) if team == team else NO_IPL_TEAM}). {percent(share)} of pressure balls bowled are in the "
            f"{PHASE_NAMES[phase]}; pressure economy {number(row.economyPressure, 2)} with "
            f"{number(row.wicketsPressure, 0)} wickets, and {number(profile[f'{phase}Economy'], 2)} in that phase. "
            + fitSentence(team, "bowling", phase, record, weakestPhase))
    return notes
