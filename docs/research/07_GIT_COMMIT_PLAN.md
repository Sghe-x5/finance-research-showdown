# Git structure and commit plan

Recommended repository layout after merge:

```text
.
├── README.md
├── DAY1_START_HERE.md
├── 02_showdown/
│   ├── PREREGISTRATION.md
│   ├── SHOWDOWN_TRACKER.md
│   ├── day1_findings.md
│   ├── day1_bdc_reporting_order.py
│   ├── day1_japan_archive_check.py
│   ├── find_nontraded_ciks.py
│   └── reporting_order.csv
├── docs/research/
│   ├── 01_DAY1_CANONICAL_FINDINGS.md
│   ├── 02_PROJECT_DECISIONS.md
│   ├── 03_PREREGISTRATION_V2.md
│   ├── 04_DAY2_EXECUTION_PLAN.md
│   ├── 05_CLAUDE_ARCHIVE_AUDIT.md
│   ├── 06_CODEX_PUSH_PROMPT.md
│   └── history/
├── artifacts/day1/
│   └── finance_project_day1_tracker_reconciled.xlsx
└── data/templates/
```

Recommended branch:

`research/day1-showdown-reconciled`

Recommended commits:

1. `fix: classify BDC result disclosures and refresh day-1 evidence`
2. `research: freeze reconciled day-1 showdown notes and preregistration`

Recommended tag:

`showdown-day1-reconciled-2026-08-12`
