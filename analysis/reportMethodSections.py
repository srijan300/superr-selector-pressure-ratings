from pipelineConfig import (
    ACTIVE_SINCE_DATE,
    BOOTSTRAP_ROUNDS,
    CROSS_VALIDATION_FOLDS,
    DIP_PROBABILITY_GATE,
    MIN_OUTING_PRESSURE_BALLS,
    MIN_PRESSURE_BALLS_BATTER,
    MIN_PRESSURE_BALLS_BOWLER,
    MIN_PRESSURE_OUTINGS,
    PRESSURE_QUANTILE,
    RECENCY_HALF_LIFE_DAYS,
    TOP_LIST_SIZE,
)
from reportTables import bulletList, figure, htmlTable, number, paragraph, percent, section, text

DATE_FORMAT = "%d %b %Y"
DAYS_PER_YEAR = 365.0


def summarySection(facts):
    pressure, batter, bowler = facts["pressure"], facts["batter"], facts["bowler"]
    points = [
        f"<b>Pressure is leverage.</b> For every ball we compute how far the batting side's win probability "
        f"is expected to swing on that delivery. The top {percent(1 - PRESSURE_QUANTILE)} of balls by this "
        f"measure are pressure balls ({number(pressure['pressureBalls'], 0)} legal deliveries). On them the "
        f"result moves {number(pressure['comparison'].loc[True, 'meanSwing'] * 100, 1)} percentage points per "
        f"ball on average, against {number(pressure['comparison'].loc[False, 'meanSwing'] * 100, 1)} on ordinary balls.",
        "<b>Performance is runs above expectation.</b> Each ball is scored against what an average player "
        "produces in the same situation against the same opposition, with dismissals priced by a "
        "data-fitted resource table. This works identically for batters and bowlers.",
        f"<b>A personal 'clutch lift' does not repeat.</b> Split the matches into random halves and a "
        f"player's pressure-minus-usual gap in one half says nothing about the other "
        f"(correlation {number(batter['splitHalf'].loc['rawLift', 'halfCorrelation'], 2)} for batters, "
        f"{number(bowler['splitHalf'].loc['rawLift', 'halfCorrelation'], 2)} for bowlers). So the rating "
        "treats the pressure record and the usual-level record as two noisy readings of one player and "
        "blends them by how informative each is.",
        f"<b>Reliability is enforced, not assumed.</b> To be listed a player must also have been above "
        f"average on pressure balls themselves and must show no credible drop from their usual level. "
        f"Every rank comes with a resampling interval and a probability of belonging in the top {TOP_LIST_SIZE}.",
    ]
    lists = '<div class="twoColumns">' + rankedList("Batters", batter["listed"]) \
        + rankedList("Bowlers", bowler["listed"]) + "</div>"
    return f'<section class="summary"><h2>Summary</h2>{bulletList(points)}{lists}</section>'


def rankedList(title, listed):
    rows = [[f"{int(row.finalRank)}", text(row.playerName), number(row.rating, 1), percent(row.topListProbability)]
            for row in listed.itertuples()]
    table = htmlTable(["Rank", title, "Rating", f"P(top {TOP_LIST_SIZE})"], rows, textColumns=2, cssClass="compact")
    return f"<div>{table}</div>"


def dataSection(facts):
    data = facts["data"]
    excludedNoBalls = data["listedMatches"] - data["matchesWithBalls"]
    points = [
        f"The pack lists {number(data['listedMatches'], 0)} matches; {number(data['matchesWithBalls'], 0)} have "
        f"ball-by-ball records ({number(data['rawBalls'], 0)} deliveries). The other {excludedNoBalls} were abandoned "
        "without a ball bowled.",
        f"We drop {data['superOverBalls']} super-over deliveries and {data['rainRevisedMatches']} rain-revised "
        "matches (revised overs or target, or a DLS result), because their targets and resources change "
        "mid-innings and would corrupt the match state.",
        f"That leaves {number(data['usedBalls'], 0)} deliveries from {number(data['usedMatches'], 0)} matches "
        f"({number(data['usedIplMatches'], 0)} IPL, {number(data['usedInternationalMatches'], 0)} T20I, the rest "
        f"emerging-team tournaments), {data['firstDate'].strftime(DATE_FORMAT)} to "
        f"{data['lastDate'].strftime(DATE_FORMAT)}.",
        f"For every delivery we rebuild the state before it is bowled: score, wickets, legal balls left, and "
        f"in a chase the target and required rate. As a check, the rebuilt totals reproduce the official "
        f"margin in {data['resultsChecked'] - data['resultMismatches']} of {data['resultsChecked']} decided "
        f"matches; the {data['resultMismatches']} exceptions differ by one run or one wicket in the source data.",
    ]
    return section("1. Data and preparation", bulletList(points))


def pressureSection(facts):
    pressure, metrics = facts["pressure"], facts["winMetrics"]
    intro = paragraph(
        "A ball is high-pressure when the match result hinges on it. We measure that directly rather than "
        "with hand-picked thresholds on required rate or wickets, which would need a different rule for "
        "every phase and would count a hopeless chase the same as a live one.")
    charts = '<div class="twoColumns">' + figure(
        "winCalibration", "Predicted against actual win rate on held-out matches.") + figure(
        "pressureHeatmap", "Share of chase balls classed as pressure, by required rate and balls left.") + "</div>"
    reading = paragraph(
        "The heatmap shows the definition behaves as cricket sense expects without being told to: pressure "
        "peaks when eight to twelve an over is needed late in a chase, and falls away both when the chase is "
        "easy and when it is already lost.")
    return section("2. Defining pressure", intro, pressureSteps(pressure, metrics), charts, reading,
                   pressureComparison(pressure), firstInningsNote(pressure))


def pressureSteps(pressure, metrics):
    return bulletList([
        "<b>Win probability.</b> Chasing: a monotone gradient-boosted model on runs required, balls left and "
        "wickets in hand (more runs needed can never help, more balls or wickets can never hurt). Batting "
        "first: a logistic model on the projected total, which is the current score plus the runs an average "
        "side adds from that many balls and wickets.",
        f"<b>Honest accuracy.</b> With {CROSS_VALIDATION_FOLDS}-fold validation that holds out whole matches, "
        f"the chase model scores AUC {number(metrics.loc[2, 'auc'], 3)} (Brier {number(metrics.loc[2, 'brier'], 3)}) "
        f"and the first-innings model AUC {number(metrics.loc[1, 'auc'], 3)} (Brier "
        f"{number(metrics.loc[1, 'brier'], 3)}). The first innings is inherently harder to call; the chart "
        "shows both are well calibrated.",
        "<b>Leverage.</b> For each ball we take the six possible outcomes (dot, 1, 2, 4, 6, wicket) with their "
        "league-wide frequency in that innings and phase, and compute the expected absolute change in win "
        "probability. Leverage is high only when the game is live <i>and</i> a single ball can move it.",
        f"<b>Pressure balls.</b> The top {percent(1 - PRESSURE_QUANTILE)} of legal deliveries by leverage "
        f"(leverage of at least {number(pressure['threshold'] * 100, 2)} percentage points).",
    ])


def firstInningsNote(pressure):
    firstLeverage, chaseLeverage = pressure["firstInningsLeverage"], pressure["chaseLeverage"]
    return paragraph(
        f"<b>What this definition does not call pressure.</b> {percent(pressure['chaseShareOfPressure'])} of "
        f"pressure balls are in the second innings ({percent(pressure['shareOfChaseBalls'])} of all chase "
        f"balls, against {percent(pressure['shareOfFirstInningsBalls'])} of first-innings balls). With no "
        f"target on the board, first-innings leverage is flat: its 10th to 90th percentile range is "
        f"{number(firstLeverage[0.1] * 100, 2)} to {number(firstLeverage[0.9] * 100, 2)} points, against "
        f"{number(chaseLeverage[0.1] * 100, 2)} to {number(chaseLeverage[0.9] * 100, 2)} in chases. Bowlers "
        "defending and batters chasing share the same pressure balls, so the method treats both disciplines "
        "symmetrically. Section 7 tests a rule-based alternative that adds first-innings collapses.")


def pressureComparison(pressure):
    comparison = pressure["comparison"]
    rows = []
    for flag, label in ((True, "Pressure balls"), (False, "Ordinary balls")):
        row = comparison.loc[flag]
        rows.append([label, number(row["balls"], 0), number(row["meanSwing"] * 100, 2), number(row["runsPerBall"], 2),
                     percent(row["wicketRate"], 1), percent(row["dotRate"], 1), percent(row["boundaryRate"], 1)])
    headers = ["", "Legal balls", "Avg win-probability swing (pts)", "Runs per ball", "Wicket", "Dot ball", "Boundary"]
    note = paragraph(
        "Pressure balls move the result several times as much, yet league-wide scoring and wicket rates are "
        "almost the same. Pressure changes what a ball is worth, not what the average player does with it, "
        "which is why differences between players have to be measured against a situation-specific expectation.")
    return htmlTable(headers, rows) + note


def performanceSection():
    points = [
        "<b>Expectation.</b> Two gradient-boosted models predict, for every delivery, the expected runs and "
        "the chance of a dismissal. Inputs: innings, over, balls left, wickets down, current and required run "
        "rate, how many balls the striker has faced, season, IPL or not, and the opposing team. The batter's "
        "version also knows whether the bowler is pace or spin; the bowler's version knows the striker's "
        "batting position and handedness.",
        f"<b>No self-scoring.</b> Predictions are out-of-fold ({CROSS_VALIDATION_FOLDS} folds, whole matches held "
        "out), so a player's ball never helps set its own expectation. Neither model is told who the player "
        "is, or the player's own team, so quality is not explained away.",
        "<b>Price of a wicket.</b> A resource table fitted on first innings gives the expected further runs "
        "from any (balls left, wickets in hand). A wicket costs the drop in that figure, capped in a chase at "
        "the runs still required.",
        "<b>Batter impact per ball</b> = (runs scored &minus; expected runs) &minus; wicket cost &times; "
        "(dismissed &minus; expected dismissal chance).",
        "<b>Bowler impact per ball</b> = (expected runs &minus; runs conceded) + wicket cost &times; (wicket "
        "taken &minus; expected wicket chance). Wides and no-balls count against the bowler; byes, leg-byes "
        "and run-outs do not.",
        "Impact is reported per 100 balls. Zero means an average player in exactly those situations; +10 "
        "means ten runs better per 100 balls.",
    ]
    return section("3. Measuring performance", bulletList(points))


def ratingSection(facts):
    batter, bowler = facts["batter"]["shrinkage"], facts["bowler"]["shrinkage"]
    finding = paragraph(
        "The brief asks how players perform under pressure <i>compared with their usual level</i>. We "
        "estimated how much players truly differ in that gap, after removing sampling noise, and the answer "
        f"for both disciplines is: not measurably (estimated variance {number(batter['liftSignalVarianceUntruncated'], 4)} "
        f"for batters and {number(bowler['liftSignalVarianceUntruncated'], 4)} for bowlers, both below zero, "
        "so set to zero). A few hundred pressure balls are too few to separate a real clutch effect from luck.")
    model = paragraph(
        "The rating is therefore the posterior mean of a player's true pressure-ball impact under a simple "
        "hierarchical model: true pressure level = true usual level + personal lift. The usual-level record "
        "and the pressure record are each weighted by their precision (recency-weighted balls divided by "
        "ball-to-ball variance), and the result is shrunk towards the average player in proportion to the "
        "remaining noise. Because lift variance is zero, a pressure ball and an ordinary ball carry equal "
        "weight per ball; had the data shown a repeatable lift, pressure balls would automatically count for more.")
    rules = bulletList([
        f"<b>Recency.</b> Balls are down-weighted with a half-life of "
        f"{number(RECENCY_HALF_LIFE_DAYS / DAYS_PER_YEAR, 0)} years, since the question is who to back in the next auction.",
        "<b>Proven under pressure.</b> A listed player's own pressure-ball impact must be above zero.",
        f"<b>No credible dip.</b> Resampling whole matches {BOOTSTRAP_ROUNDS} times, the chance that the "
        f"player's pressure impact is below their usual impact must be under {percent(DIP_PROBABILITY_GATE)}.",
        f"<b>Consistency</b> is reported as the share of pressure outings (at least {MIN_OUTING_PRESSURE_BALLS} "
        "pressure balls in a match) with positive total impact. It is shown as evidence, not scored, because "
        "it too fails to repeat between halves for batters.",
    ])
    return section("4. From balls to a rating", finding, model, rules)


def fairnessSection(facts):
    points = [
        f"<b>Eligibility.</b> At least {MIN_PRESSURE_BALLS_BATTER} pressure balls faced (batters) or "
        f"{MIN_PRESSURE_BALLS_BOWLER} bowled (bowlers), at least {MIN_PRESSURE_OUTINGS} pressure outings, and a "
        f"match on or after {ACTIVE_SINCE_DATE}. {len(facts['batter']['ratings'])} batters and "
        f"{len(facts['bowler']['ratings'])} bowlers qualify.",
        "<b>Sample size.</b> Shrinkage does the work: a player with few balls is pulled towards average, so "
        "a short hot streak cannot top the list. The posterior standard deviation is reported beside every rating.",
        "<b>IPL and T20I together.</b> Both are used, because pressure balls are scarce. The expectation "
        "models carry the opposing team and an IPL flag, so runs against a weak attack are worth less than "
        "runs against a strong one. Section 7 reruns the rating on IPL matches alone.",
        "<b>Match context.</b> Phase, wickets down, run rates and the batter's time at the crease are in the "
        "expectation, so openers, finishers, powerplay and death bowlers are each compared with their own situations.",
    ]
    return section("5. Fair comparisons", bulletList(points))
