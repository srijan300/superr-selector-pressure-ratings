from pipelineConfig import BOOTSTRAP_ROUNDS, SPLIT_HALF_ROUNDS
from reportTables import bulletList, figure, htmlTable, number, paragraph, percent, section, signed, text


def evidenceSection(facts):
    intro = paragraph(
        "Rating and impacts are runs per 100 balls better than an average player in the same situations. "
        f"'Range' is the 5th to 95th percentile of the player's rank over {BOOTSTRAP_ROUNDS} resamples of whole matches.")
    return section("6. Evidence for the top 10", intro, batterEvidence(facts["batter"]), bowlerEvidence(facts["bowler"]))


def batterEvidence(role):
    rows = []
    for row in role["listed"].itertuples():
        rows.append([f"{int(row.finalRank)}", text(row.playerName), f"{number(row.rating)} &plusmn; {number(row.posteriorSd)}",
                     number(row.ballsPressure, 0), number(row.strikeRatePressure, 0), number(row.averagePressure),
                     number(row.strikeRateBaseline, 0), signed(row.rawPressureImpact), signed(row.rawBaselineImpact),
                     percent(row.rawOutingRate), f"{number(row.rankLow, 0)}-{number(row.rankHigh, 0)}"])
    headers = ["#", "Batter", "Rating &plusmn; sd", "Pressure balls", "Pressure SR", "Pressure avg", "Usual SR",
               "Pressure impact", "Usual impact", "Outings above par", "Range"]
    chart = figure("batterPressureVersusUsual",
                   "Batters: usual level, pressure record and the blended rating. The rating sits left of both "
                   "because it is shrunk towards the average player (zero).")
    return "<h3>Batters</h3>" + htmlTable(headers, rows, textColumns=2, cssClass="compact") + skippedNote(role) + chart


def bowlerEvidence(role):
    rows = []
    for row in role["listed"].itertuples():
        rows.append([f"{int(row.finalRank)}", text(row.playerName), text(row.pace_or_spin),
                     f"{number(row.rating)} &plusmn; {number(row.posteriorSd)}", number(row.ballsPressure, 0),
                     number(row.economyPressure, 2), number(row.wicketsPressure, 0), number(row.economyBaseline, 2),
                     signed(row.rawPressureImpact), signed(row.rawBaselineImpact), percent(row.rawOutingRate),
                     f"{number(row.rankLow, 0)}-{number(row.rankHigh, 0)}"])
    headers = ["#", "Bowler", "Type", "Rating &plusmn; sd", "Pressure balls", "Pressure econ", "Pressure wkts",
               "Usual econ", "Pressure impact", "Usual impact", "Outings above par", "Range"]
    chart = figure("bowlerPressureVersusUsual", "Bowlers: usual level, pressure record and the blended rating.")
    return "<h3>Bowlers</h3>" + htmlTable(headers, rows, textColumns=3, cssClass="compact") + skippedNote(role) + chart


def skippedNote(role):
    """Players the rating placed inside the list but the two reliability rules removed."""
    if role["skipped"].empty:
        return ""
    reasons = []
    for row in role["skipped"].itertuples():
        reasons.append(f"{text(row.playerName)} (rated {int(row.rank)}; pressure impact {signed(row.rawPressureImpact)}, "
                       f"dip probability {percent(row.dipProbability)})")
    return paragraph("<b>Rated high enough but not listed</b>, because their own pressure record is below "
                     "average or credibly below their usual level: " + "; ".join(reasons) + ".")


def reliabilitySection(facts):
    batter, bowler = facts["batter"], facts["bowler"]
    splitText = paragraph(
        f"<b>Consistency across matches.</b> We split the matches into two random halves {SPLIT_HALF_ROUNDS} "
        "times and correlated each measure between halves across eligible players. The headline rating "
        "repeats; a rating built on the pressure record alone barely does for batters, and the lift does not at all.")
    heldOutRows = []
    for key in batter["heldOut"].index:
        heldOutRows.append([text(batter["heldOut"].loc[key, "description"]).capitalize(),
                            number(batter["heldOut"].loc[key, "correlationWithHeldOutPressureImpact"], 2),
                            number(bowler["heldOut"].loc[key, "correlationWithHeldOutPressureImpact"], 2)])
    heldOutText = paragraph(
        "<b>Does it predict pressure performance?</b> The stricter test: build each estimate on one half of "
        "the matches and correlate it with raw pressure-ball impact in the other half. The blended rating is "
        "the best predictor in both disciplines. The correlations are modest because half a player's pressure "
        "balls is itself a very noisy target.")
    heldOutTable = htmlTable(["Estimate built on half A", "Batters", "Bowlers"], heldOutRows)
    intervals = figure(
        "batterRankIntervals", "Batters: rank spread under resampling; the label shows P(top 10). Grey = not listed.",
        "narrow") + figure("bowlerRankIntervals", "Bowlers: rank spread under resampling. Grey = not listed.", "narrow")
    return section("7. Reliability and limitations", splitText, figure("splitHalfReliability",
                   "Split-half correlation of each measure.", "narrow"), heldOutText, heldOutTable,
                   paragraph("<b>How firm is each rank?</b> The first three or four batters are secure. "
                             "Bowlers are closer together, and from about fifth place down in either list "
                             "the intervals overlap heavily, so adjacent ranks are close calls."),
                   intervals, sensitivityBlock(batter, bowler), limitationsBlock(facts))


def sensitivityBlock(batter, bowler):
    rows = []
    for position in range(len(batter["sensitivity"])):
        batterRow, bowlerRow = batter["sensitivity"].iloc[position], bowler["sensitivity"].iloc[position]
        rows.append([text(batterRow["variant"]),
                     f"{int(batterRow['topListOverlap'])} of {int(batterRow['headlineTopStillEligible'])}",
                     number(batterRow["rankCorrelation"], 2),
                     f"{int(bowlerRow['topListOverlap'])} of {int(bowlerRow['headlineTopStillEligible'])}",
                     number(bowlerRow["rankCorrelation"], 2)])
    headers = ["Change one assumption", "Batters: top 10 kept", "Rank corr.", "Bowlers: top 10 kept", "Rank corr."]
    note = paragraph(
        "<b>Sensitivity.</b> 'Top 10 kept' counts how many of the headline top-rated ten stay in the top ten, "
        "out of those still eligible under the variant. Rank correlation is over all players eligible in both.")
    return note + htmlTable(headers, rows)


def limitationsBlock(facts):
    pressure = facts["pressure"]
    smallest = facts["batter"]["listed"].sort_values("ballsPressure").iloc[0]
    spreads = [facts[role]["listed"]["posteriorSd"] for role in ("batter", "bowler")]
    lowestSpread, highestSpread = min(spread.min() for spread in spreads), max(spread.max() for spread in spreads)
    points = [
        f"<b>Pressure here is chase pressure.</b> {percent(pressure['chaseShareOfPressure'])} of pressure balls "
        "are second-innings. A first-innings rescue after a collapse is not rewarded as pressure; the "
        "rule-based variant above shows how much the lists move when it is.",
        f"<b>Ranks are estimates.</b> Posterior standard deviations run from {number(lowestSpread)} to "
        f"{number(highestSpread)} runs per 100 balls, larger than most gaps between neighbours. {text(smallest['playerName'])} has the thinnest "
        f"pressure sample in the batting list ({number(smallest['ballsPressure'], 0)} balls).",
        "<b>The rating leans on overall quality.</b> That is what the data support, but it means a player "
        "with a genuine, as yet undetectable clutch trait gets little extra credit.",
        "<b>State-based win probability.</b> It ignores team strength, venue, dew and pitch, so leverage is "
        "the same for any two sides in the same position.",
        "<b>Opposition is adjusted by team, not by individual.</b> Facing a side's best bowler and its "
        "fifth bowler are treated alike beyond the pace or spin flag.",
        "<b>Not measured:</b> fielding, running between wickets for the non-striker, captaincy, and whether "
        "a player will actually be available at the auction.",
    ]
    return "<h3>Limitations</h3>" + bulletList(points)


def reproduceSection():
    steps = bulletList([
        "<code>buildPressureStates.py</code>: match state, win-probability models, leverage, pressure flag.",
        "<code>buildBallImpacts.py</code>: out-of-fold expectation models and per-ball impact.",
        "<code>buildRatings.py</code>: hierarchical ratings, bootstrap, split-half, held-out and sensitivity checks.",
        "<code>buildProfiles.py</code>, <code>reportCharts.py</code>, <code>buildReport.py</code>: profiles, charts, this document.",
        "<code>validateState.py</code>: checks rebuilt totals against official results.",
    ])
    return section("9. Reproducing this analysis",
                   paragraph("Python with pandas, scikit-learn and matplotlib; fixed random seed. All thresholds "
                             "live in <code>pipelineConfig.py</code>. Run <code>runPipeline.py</code>, or the "
                             "stages in order. Every number and table in this report is read from the "
                             "pipeline's output files when the document is built."), steps)
