# CSV Position Reconciliation

A Python command-line tool that reconciles calculated closing positions
against reference positions supplied as CSV files.

This project demonstrates CSV input validation, position calculation,
discrepancy reporting, automated testing, and reproducible runs using
synthetic data.

## Reconciliation Logic

For each account and symbol:

```text
Calculated closing position = opening position + BUY quantities - SELL quantities

Difference = calculated closing position - reference position
```

The tool compares position quantities, not prices or market values.

## Features

- Calculate closing positions from opening balances and daily trades.
- Reconcile positions by account and symbol.
- Validate CSV schemas, field values, and duplicate records.
- Generate CSV and HTML reconciliation reports.
- Preserve input snapshots and run metadata.
- Generate an HTML run-history page.
- Demonstrate matching, mismatching, and invalid-input scenarios.
- Include unit, regression, and end-to-end tests.

## Quick Start

Download or clone this repository, then open a terminal in the repository
root directory.

The commands below use `python3`. If your Python installation uses
`python` instead, substitute that command.

### 1. Run the Tests

```bash
python3 -m unittest discover -v
```

The release candidate passed 37 tests locally. GitHub Actions checks the
committed version separately.

### 2. Run the Matching Example

```bash
python3 run_workflow.py --trades examples/match/trades.csv --opening examples/match/opening.csv --reference examples/match/reference.csv --output-dir outputs
```

Expected result:

| Item | Value |
| --- | --- |
| Opening position | 50 |
| BUY quantity | 20 |
| SELL quantity | 10 |
| Calculated closing position | 60 |
| Reference position | 60 |
| Difference | 0 |
| Exit code | 0 |

CSV and HTML reports are generated.

### 3. Run the Mismatching Example

```bash
python3 run_workflow.py --trades examples/mismatch/trades.csv --opening examples/mismatch/opening.csv --reference examples/mismatch/reference.csv --output-dir outputs
```

Expected result:

- Calculated closing position: 60.
- Reference position: 61.
- Difference: -1.
- CSV and HTML reports are generated.
- Exit code: 1, indicating reconciliation exceptions.

### 4. Run the Invalid-Input Example

```bash
python3 run_workflow.py --trades examples/invalid/trades.csv --opening examples/invalid/opening.csv --reference examples/invalid/reference.csv --output-dir outputs
```

Expected result:

- A duplicate trade ID is rejected.
- A failure manifest is retained.
- No reconciliation report is generated.
- Exit code: 2.

The nonzero exit codes in the mismatching and invalid-input examples
are intentional.

### 5. Generate the History Page

```bash
python3 view_history.py --output-dir outputs
```

Open `outputs/index.html` in a browser to inspect run statuses and
available report links.

## Input Formats

### Trades

```csv
trade_id,account,symbol,side,quantity
DEMO_T001,DEMO_ACCOUNT,DEMO_STOCK,BUY,20
DEMO_T002,DEMO_ACCOUNT,DEMO_STOCK,SELL,10
```

### Opening Positions

```csv
account,symbol,quantity
DEMO_ACCOUNT,DEMO_STOCK,50
```

### Reference Positions

```csv
account,symbol,quantity
DEMO_ACCOUNT,DEMO_STOCK,60
```

All bundled example records are synthetic.

## Exit Codes

| Code | Meaning |
| --- | --- |
| 0 | Reconciliation completed with matching positions |
| 1 | Reconciliation completed with exceptions |
| 2 | Input or execution error; inspect the error output |

## Project Structure

| File or directory | Purpose |
| --- | --- |
| `reconcile.py` | Core reconciliation logic |
| `reconcile_daily.py` | Closing-position calculation |
| `reconcile_cli.py` | Command-line reconciliation |
| `validate_inputs.py` | CSV input validation |
| `report_html.py` | HTML report generation |
| `run_workflow.py` | Workflow orchestration |
| `view_history.py` | Run-history page generation |
| `test_*.py` | Automated tests |
| `examples/` | Synthetic CSV inputs |
| `.github/workflows/tests.yml` | GitHub Actions test configuration |
| `outputs/` | Generated local outputs; excluded from version control |

## Automated Testing

The GitHub Actions configuration runs the test suite on Ubuntu with
Python 3.12 for pushes, pull requests, and manual workflow runs.

To run the same test command locally:

```bash
python3 -m unittest discover -v
```

Cloud test results are available in the repository's Actions tab.

## Scope and Limitations

This is a portfolio and learning project, not a production trading,
accounting, or regulatory reporting system.

It does not implement:

- Broker connectivity or live trading.
- Settlement processing.
- Corporate actions.
- Market valuation.
- Production access controls.

Input snapshots and run metadata help explain individual runs,
but do not constitute a tamper-proof audit trail.

## Data Privacy

Use synthetic data for public demonstrations.

Do not commit real account data, confidential trades, credentials,
or generated reports containing sensitive information.

Generated outputs may contain input snapshots and local filesystem
paths. Keep these files out of the public repository.
