# Day 5 Phase A event-review freeze

Status: **frozen outcome-blind human consensus**

- Final consensus SHA-256: `aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b`
- Frozen blind packet SHA-256: `4f7c0e8941a321a7e95d5395ce60182f380a063933dc2f2c8dc5373771172625`
- Preregistration draft SHA-256: `65bf2b2a88cc61521eaaf2dd0e43af8a992a6fb4d1c1cc0dd4d8ef3bb434fd44`
- Evaluator SHA-256: `ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4`
- Reviewer X input SHA-256: `10c1205b431138c0c9c9e945e72cee7cdf3b0eba6301498af3010d765f02909e`
- Reviewer Y input SHA-256: `eac24a94217df0afd314d4cb3adca02f3a394e666cc84d25de709d328406a877`
- Adjudicator H SHA-256: `bbe51c86848a7b8d873ae617474e602a86a0c3b4deeaacc438243ea8f52dedb2`

The final file contains exactly 75 unique review IDs in the original blind-packet order. All non-review fields are byte-for-byte equal after CSV parsing, every inclusion label satisfies the locked mechanical rule, and the counts are 67 `yes`, 7 `uncertain`, and 1 `no`. The 67 included blind-union rows contain 67 source-event clusters and 33 normalized borrowers.

At this commit boundary the private STRICT/SUPPORTING membership key had not been opened. Target-current structure, valuation values, predictions, errors, and model results also remained unopened. Human labels and notes were not changed.
