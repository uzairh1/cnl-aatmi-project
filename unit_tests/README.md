# test_scripts

## Purpose

pytest unit tests.

Use these scripts while developing or refactoring modules. They are
intentionally verbose and may print intermediate DataFrames, paths, and
diagnostic information.

## Philosophy

-   Fake data first.
-   Real data second.
-   Unit tests verify isolated logic.
-   Manual scripts help understand behavior interactively.

## Current Manual Scripts

### test_ttl_table_parser.py

Creates a synthetic TTL table resembling the real experiment.

Verifies:

-   experimentPhase filtering
-   movieID filtering
-   timing conversion
-   derived analysis columns
-   CSV writing

Input: - In-memory fake DataFrame

Output: - `trial_table.csv` - Printed DataFrame summary

### test_localization.py

Creates a synthetic localization table.

Verifies:

-   workbook loading
-   neuron filename parsing
-   localization lookup
-   returned anatomical labels

