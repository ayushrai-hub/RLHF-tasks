Write an R script at /app/analysis.R for the causal task described in /app/docs/estimand_contract.md. Read main.csv and params.json from the directory named by CAUSAL_DATA_DIR, defaulting to /app/data when the variable is unset.

Use only the supplied input files, compute the requested estimate at run time, and write /app/estimate.json as a JSON object with a finite numeric estimate value. Do not hardcode values from the visible data or read from solution or tests paths.
