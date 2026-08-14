# Project Goal and Constraints

## Career goal

Two software engineers want one shared financial project strong enough to support
applications to hedge funds, asset managers, proprietary research teams, quant/data
engineering teams, and AI research-product roles outside Russia.

The project should demonstrate:

- original hypothesis formation;
- financial-domain learning;
- point-in-time data engineering;
- messy entity/facility resolution;
- LLM use where it is genuinely necessary;
- calibrated numerical modeling;
- reproducible research;
- live immutable predictions;
- honest null-result handling;
- production-like research tooling for analysts.

The product does **not** need to autonomously trade. A strong outcome is a system
that creates differentiated, auditable information for an analyst or PM.

## Resources

- Two MacBook Pro laptops.
- One machine: Apple M3, 32 GB unified memory, 1 TB SSD.
- ChatGPT Pro/Codex.
- Local Python, DuckDB/Parquet/SQLite/Postgres.
- Local LLMs through Ollama/MLX when useful.
- Initial budget: zero.
- Total discretionary budget target: roughly RUB 5,000.
- No Bloomberg, FactSet, I/B/E/S, expensive historical options, or institutional
  datasets as a required core dependency.

## Non-negotiable research rules

- Point-in-time data only.
- Exact public timestamps, not period-end dates as availability timestamps.
- LLM extracts evidence; it does not invent trading probabilities.
- Every prediction and model version is hashable and reproducible.
- No random train/test split for time-series event research.
- No survivorship or delisting omissions.
- No silent sample replacement.
- `NO TRADE` / abstention must be allowed.
- Null results are acceptable if a useful dataset, benchmark, or research product remains.
- No claims such as “first in the world,” “nobody does this,” or “guaranteed alpha”
  without proof.
- No private keys, secrets, employer data, or hidden reviewer mappings in Git.
