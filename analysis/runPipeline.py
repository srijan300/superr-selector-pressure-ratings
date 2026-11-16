"""Run every stage in order: python analysis/runPipeline.py"""
import buildBallImpacts
import buildDashboardData
import buildPressureStates
import buildProfiles
import buildRatings
import buildReport
import reportCharts

STAGES = (buildPressureStates, buildBallImpacts, buildRatings, buildProfiles, reportCharts, buildReport,
          buildDashboardData)


def main():
    for stage in STAGES:
        print(f"--- {stage.__name__}")
        stage.main()


if __name__ == "__main__":
    main()
