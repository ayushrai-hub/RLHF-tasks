# predictions.csv

Written to /app/outputs/predictions.csv with one row per held-out test instance, columns in this order:

- row_id: int, the 0-based row index of the instance in /app/data/tvs_loan.csv
- pred_proba: float, predicted probability that V32 == 1 (default), in [0, 1], rounded to 6 decimals
- pred_label: int, 0 or 1, the approve-or-decline decision at your chosen cost-optimal threshold (1 means flag as a likely defaulter)

Rows sorted by row_id ascending. The set of row_id values equals the rows marked test in /app/data/split.csv.
