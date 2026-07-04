import base64
import gzip
import os
import subprocess
from pathlib import Path

import pytest

HIDDEN_LABELS_B64_GZ = "H4sIAAAAAAACE3WZ3W4bOQyF7/dZfCH+SJSexnATow3QxoGT7iJvv7bjAvXw40UAh8OhSJGHOkOdT//tX553b+fTx+np9HN/+HV8fb78fey//T4/H19372+n1/fTef/x+XbcnQ/n4/755f14eD/uvh9fj/uPH8fz4e3zH2kuu7Z7/3X4+XP/7eX0cXz6cfm/XR/o5cfL6/Pv94/z506+ZPa37K7nl4ePBmQn1wcdlMflx+Hp8Hz89fL0RxYgm5cf30//Hs+v16j+LL9I2lt+v19cSDJNkd4NQFTdK+X+6MNdfWw9u+5Ah8j6/Ft2t7mybLTLj41TQ0Cm5M+wvPJwkPWLxfw2ZGkErD1ziYyVdz4a5S0eornLNK8cEEt49iY66A3anYC8BOQlVtabrSj3KdulblJN6nc7ltebTt5OrLg5aE9n5N2fM5f3XHn/FuBoAY6WFh1jWfUA41r9b9tf/q/xWI93KeRrYYdYK8UqLcclTRje0hQAIc04i5eWBOt1kI3KQMDWXPIDJhZpSsuaktuEiOLbGVoiRecT6dWDTbuQqyxSeYtM9GGlMhDNzU9Usq+qqTxFq1ypZzeVsCU6ikgVs6W5dYiubSFfl7NG71txBIvlbihmeWvMQa8DPsRGLhfDoAxK0Fbq9+KtcP5GLDYGHNHlBi319gDQ5b1SHpUjuXuIQ3SOAOuYsl6lrEPK+qbVXysB+MVduYOBKrQetJ8dcdYxvAHNcQiVDhINuRGNLIWCHNAWRxXYCHRhgtlVYDUgsoAeEliTUZxlEg5MTwL7SGzQdtOEagxMWOQzWiZW4wSoVcRDplG802nDJ+RsZnIoM0Bv4jqr2NdV9ZFVQW1hQS57ZJXXPUf+IavnbnbjHxuorgBiJwtztghk2hpKi8C05S8vbfkbRVtGmbYOsgHvEsC0TXR0cSnpI/n4MiFCJkSzC0A+VByKRqXD2yMduioBehNWwSxpK8LUKlGqfBapGjclVYxPe7XAeNxgucqiUiZGrJq/x9QyaVQTkGneY4OsPfKPux7kzOhrTC3AImTNitahntmiuqQzV10rA1Y9cLBSJcsBZo4wc4jOM7dSmGxol8RiFUiH9swTtXv64lacZ2iHWLZk4/7+RGn+claYaOjAboFUQ4dlMAwHGUY0RsbBqKAEREMHhBQApAAgwVhDAzp60EGlAVCKARarcCLPaTQqNCHF0ClFc5zQ2WeFp+nZkVnhaY5cLzNABsma2OErjqEr80Ktxhy6AFkL6nDRF5guQNaCc2tNkOXphsF0wxqhypqitMiVtdzUrfVKefBJaC3AZWoZ1oqCNBhxmAjItDJgqe2ZOJA6E2odJqMyHKg+UVqFp616ADFqbiSmBjIHWQfZABmkTCfoEcbMcpe3R27xlQBTQIcBuzDz1LkN2IUhuzCDaIw+TcxoZGM3crGBAd6Z3JRzMzQ3ChRGGwYXJgYXJubBvdh8Vg/y2WVALqzTl791iKoXDNc6tI3eC7+qwYZ1RNZtsIHqFbhGBa4h1QPskjjmsAFJhDGHwX2KjTwgtTHh3So0mG9YYOOPqjEGRhVeZCt6hjbwEAuAXCDkAiE3oeFX/MOqOYfNqkKnF2fV7OkQtzkq8wXZstvcY9PsJl1c2iKmZdW8wypCYgua5sLz7fHK5a450DcE4KoAuIoq9dY4C44cxVtuNd5yeN4c3+6VFxSjt6jUcwq95WmcS4Pydclk0kVBZkCDXDJFdqFbWq9oiW/vXm5OTXCgSppmADqwEVfI1u36ZbOQOuhlNuI6QC9ojxUyhHzEje6evbpycdPqgaH1zLMcuInDvYsDM3GDuKwYv7lDmhxh5VB+DolymgK7Q6qAlzhctLgXHcO9iirzkv8Bvynsou0iAAA="
CHECK_NAMES = ['schema','validation_schema','coverage','probability_values','metrics_schema','reported_validation','hidden_quality','probability_diversity','suspicious_perfection','hidden_target_absent']
CHECK_IDS = ['prediction-columns','validation-columns','row-coverage-and-order','probability-values','metrics-fields-and-types','validation-auroc-reported','hidden-classification-quality','probability-diversity','not-suspiciously-perfect','target-not-visible-in-test']
R_TEST_CODE = r"""
library(jsonlite)
out <- Sys.getenv('OUTPUT_DIR', '/app/output')
data_dir <- Sys.getenv('DATA_DIR', '/app/data')
label_table <- Sys.getenv('HIDDEN_LABEL_TABLE')
if (!nzchar(label_table)) stop('missing hidden label table')
preds <- read.csv(file.path(out, 'predictions.csv'), stringsAsFactors = FALSE)
vp <- read.csv(file.path(out, 'validation_predictions.csv'), stringsAsFactors = FALSE)
metrics <- fromJSON(file.path(out, 'metrics.json'))
test_raw <- read.csv(file.path(data_dir, 'test.csv'), stringsAsFactors = FALSE, na.strings = c('', 'NA'))
valid <- read.csv(file.path(data_dir, 'validation.csv'), stringsAsFactors = FALSE, na.strings = c('', 'NA'))
train <- read.csv(file.path(data_dir, 'train.csv'), stringsAsFactors = FALSE, na.strings = c('', 'NA'))
labels <- read.csv(text = label_table, stringsAsFactors = FALSE)
merged <- merge(labels, preds, by = 'row_id')
fail <- function(msg) stop(msg, call. = FALSE)
auc_rank <- function(y, p) { y <- as.integer(y); r <- rank(as.numeric(p), ties.method = 'average'); n1 <- sum(y == 1); n0 <- sum(y == 0); (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0) }
brier <- function(y, p) mean((as.numeric(y) - as.numeric(p)) ^ 2)
ba_label <- function(y, lab) (mean(lab[y == 1] == 1) + mean(lab[y == 0] == 0)) / 2
checks <- list(
  schema = function() { if (!identical(names(preds), c('row_id','pred_label','pred_proba_positive'))) fail('prediction columns do not match') },
  validation_schema = function() { if (!identical(names(vp), c('row_id','pred_label','pred_proba_positive'))) fail('validation columns do not match') },
  coverage = function() { if (nrow(preds) != 410 || any(preds$row_id != sort(test_raw$row_id)) || any(duplicated(preds$row_id))) fail('test coverage mismatch'); if (nrow(vp) != 260 || any(vp$row_id != sort(valid$row_id)) || any(duplicated(vp$row_id))) fail('validation coverage mismatch') },
  probability_values = function() { if (!all(preds$pred_label %in% c(0,1)) || !all(vp$pred_label %in% c(0,1))) fail('labels must be binary'); if (any(!is.finite(preds$pred_proba_positive)) || any(preds$pred_proba_positive < 0 | preds$pred_proba_positive > 1) || any(!is.finite(vp$pred_proba_positive)) || any(vp$pred_proba_positive < 0 | vp$pred_proba_positive > 1)) fail('probabilities invalid') },
  metrics_schema = function() { req <- c('n_train','n_test','primary_metric_value','validation_balanced_accuracy','validation_rare_disease_balanced_accuracy','validation_brier','predicted_positive_rate','model_family','missing_value_strategy','text_feature_strategy','final_fit_rows','temporal_split_year'); if (!setequal(names(metrics), req)) fail('metrics keys do not match'); if (as.integer(metrics$n_train) != nrow(train) + nrow(valid) || as.integer(metrics$final_fit_rows) != nrow(train) + nrow(valid) || as.integer(metrics$n_test) != 410 || as.integer(metrics$temporal_split_year) != 2025) fail('count metadata mismatch'); if (!is.character(metrics$model_family) || nchar(metrics$model_family) == 0 || !is.character(metrics$missing_value_strategy) || nchar(metrics$missing_value_strategy) == 0 || !is.character(metrics$text_feature_strategy) || nchar(metrics$text_feature_strategy) == 0) fail('method metadata missing') },
  reported_validation = function() { got <- merge(valid[, c('row_id','protocol_amendment_burden','rare_disease')], vp, by = 'row_id'); au <- auc_rank(got$protocol_amendment_burden, got$pred_proba_positive); vba <- ba_label(got$protocol_amendment_burden, got$pred_label); rare <- got$rare_disease == 1; vrba <- ba_label(got$protocol_amendment_burden[rare], got$pred_label[rare]); vb <- brier(got$protocol_amendment_burden, got$pred_proba_positive); pr <- mean(preds$pred_label == 1); if (abs(as.numeric(metrics$primary_metric_value) - au) > 0.01 || au < 0.80 || abs(as.numeric(metrics$validation_balanced_accuracy) - vba) > 0.01 || vba < 0.69 || abs(as.numeric(metrics$validation_rare_disease_balanced_accuracy) - vrba) > 0.01 || vrba < 0.60 || abs(as.numeric(metrics$validation_brier) - vb) > 0.01 || vb > 0.14 || abs(as.numeric(metrics$predicted_positive_rate) - pr) > 0.01) fail('validation or reported positive-rate requirements were not met') },
  hidden_quality = function() { au <- auc_rank(merged$protocol_amendment_burden, merged$pred_proba_positive); bb <- ba_label(merged$protocol_amendment_burden, merged$pred_label); br <- brier(merged$protocol_amendment_burden, merged$pred_proba_positive); small <- merged$sponsor_type == 'small_biotech' & merged$protocol_amendment_burden == 1; small_recall <- mean(merged$pred_label[small] == 1); rare <- merged$rare_disease == 1; rare_ba <- ba_label(merged$protocol_amendment_burden[rare], merged$pred_label[rare]); base <- brier(merged$protocol_amendment_burden, rep(mean(train$protocol_amendment_burden), nrow(merged))); brier_margin <- base - br; pos_rate <- mean(merged$pred_label == 1); msg <- sprintf('hidden classification quality requirements were not met: auroc=%.4f min=0.7700, balanced_accuracy=%.4f min=0.6900, brier=%.4f max=0.1600, small_biotech_positive_recall=%.4f min=0.6000, rare_disease_balanced_accuracy=%.4f min=0.6100, predicted_positive_rate=%.4f required=[0.2400,0.3600], brier_baseline_margin=%.4f min=0.0100', au, bb, br, small_recall, rare_ba, pos_rate, brier_margin); if (au < 0.77 || bb < 0.69 || br > 0.16 || small_recall < 0.60 || rare_ba < 0.61 || pos_rate < 0.24 || pos_rate > 0.36 || brier_margin < 0.01) fail(msg) },
  probability_diversity = function() { if (length(unique(round(preds$pred_proba_positive, 4))) < 40 || sd(preds$pred_proba_positive) < 0.07) fail('probabilities are insufficiently varied') },
  suspicious_perfection = function() { if (brier(merged$protocol_amendment_burden, merged$pred_proba_positive) < 0.015) fail('predictions are implausibly perfect') },
  hidden_target_absent = function() { runtime <- read.csv(file.path(data_dir, 'test.csv'), stringsAsFactors = FALSE, na.strings = c('', 'NA')); if ('protocol_amendment_burden' %in% names(runtime)) fail('test target column should be absent') }
)
checks[[Sys.getenv('CHECK_NAME')]]()
"""

def test_predictions_file_exists():
    """The test prediction CSV is present before detailed R checks run."""
    assert (Path(os.environ.get('OUTPUT_DIR', '/app/output')) / 'predictions.csv').exists()

def test_validation_predictions_file_exists():
    """The validation prediction CSV is present before detailed R checks run."""
    assert (Path(os.environ.get('OUTPUT_DIR', '/app/output')) / 'validation_predictions.csv').exists()

def test_metrics_file_exists():
    """The metrics JSON is present before detailed R checks run."""
    assert (Path(os.environ.get('OUTPUT_DIR', '/app/output')) / 'metrics.json').exists()

@pytest.mark.parametrize('check_name', CHECK_NAMES, ids=CHECK_IDS)
def test_r_verifier(check_name):
    """Run one named R check for schema, coverage, quality, or output consistency."""
    path = Path('/tmp/healthstat_r_check.R')
    path.write_text(R_TEST_CODE)
    env = os.environ.copy()
    env['CHECK_NAME'] = check_name
    env['HIDDEN_LABEL_TABLE'] = gzip.decompress(base64.b64decode(HIDDEN_LABELS_B64_GZ)).decode()
    subprocess.run(['Rscript', str(path)], check=True, env=env)
