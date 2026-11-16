"""Check the rebuilt innings totals against the official result text in matches.csv.

A "won by N runs" result requires firstInningsTotal - secondInningsTotal == N.
A "won by N wickets" result requires 10 - wicketsLost == N and the chase total to reach the target.
Run by hand: python analysis/validateState.py
"""
import re

import pandas as pd

from dataLoader import loadBalls, loadMatches
from matchState import buildBallStates
from pipelineConfig import WICKETS_PER_INNINGS

RUN_MARGIN_PATTERN = re.compile(r"won\s*(?:by)?\s*(\d+)\s*runs?\b", re.IGNORECASE)
WICKET_MARGIN_PATTERN = re.compile(r"won\s*(?:by)?\s*(\d+)\s*(?:wickets?|wkts)\b", re.IGNORECASE)


def main():
    matches = loadMatches()
    states = buildBallStates(loadBalls(), matches)
    counts, runMismatches, wicketMismatches = validateAgainstResults(states, matches)
    print(counts)
    print(runMismatches.to_string())
    print(wicketMismatches.to_string())


def validateAgainstResults(states, matches):
    summary = summariseInnings(states).join(matches.set_index("match_id")["result"])
    runChecked, runMismatches = checkRunMargins(summary)
    wicketChecked, wicketMismatches = checkWicketMargins(summary)
    counts = {"matchesWithState": len(summary), "resultsChecked": runChecked + wicketChecked,
              "mismatches": len(runMismatches) + len(wicketMismatches)}
    return counts, runMismatches, wicketMismatches


def summariseInnings(states):
    totals = states.groupby(["match_id", "innings"]).agg(
        total=("inningsTotal", "first"), wickets=("is_wicket", "sum"))
    wide = totals.unstack("innings")
    wide.columns = [f"{name}{innings}" for name, innings in wide.columns]
    return wide


def checkRunMargins(summary):
    margin = summary["result"].str.extract(RUN_MARGIN_PATTERN)[0].astype(float)
    checked = summary[margin.notna()].copy()
    checked["statedMargin"] = margin[margin.notna()]
    checked["rebuiltMargin"] = checked["total1"] - checked["total2"]
    return len(checked), checked[checked["statedMargin"] != checked["rebuiltMargin"]]


def checkWicketMargins(summary):
    margin = summary["result"].str.extract(WICKET_MARGIN_PATTERN)[0].astype(float)
    checked = summary[margin.notna()].copy()
    checked["statedMargin"] = margin[margin.notna()]
    checked["rebuiltMargin"] = WICKETS_PER_INNINGS - checked["wickets2"]
    checked["reachedTarget"] = checked["total2"] > checked["total1"]
    wrong = (checked["statedMargin"] != checked["rebuiltMargin"]) | ~checked["reachedTarget"]
    return len(checked), checked[wrong]


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    main()
