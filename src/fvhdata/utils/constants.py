from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parent.parent.parent.parent

DATA = REPOSITORY_ROOT.joinpath("data")
RAW = DATA.joinpath("raw")
INTERIM = DATA.joinpath("interim")
PROCESSED = DATA.joinpath("processed")

REPORTS = REPOSITORY_ROOT.joinpath("reports")
FIGURES = REPORTS.joinpath("figures")
