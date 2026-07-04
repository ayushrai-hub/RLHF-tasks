source('/app/helpers/load_data.R')
source('/app/helpers/preprocessing.R')
source('/app/helpers/metrics.R')
dir.create('/app/output', showWarnings = FALSE, recursive = TRUE)
train <- read_task_csv('train.csv')
valid <- read_task_csv('validation.csv')
test <- read_task_csv('test.csv')
target <- 'protocol_amendment_burden'
site_med <- median(train$sites_planned, na.rm = TRUE)
engineer <- function(df) {
  df$sites_missing <- as.integer(is.na(df$sites_planned))
  df$sites_planned[is.na(df$sites_planned)] <- site_med
  df$log_enrollment <- log1p(df$enrollment)
  df$log_sites <- log1p(df$sites_planned)
  dur_c <- (df$duration_months - 20) / 12
  sit_c <- (df$log_sites - 1.2) / 0.7
  elig_c <- (df$eligibility_word_count - 210) / 60
  df$dur_site_mismatch <- dur_c * sit_c
  df$gene_eligibility <- df$gene_therapy * elig_c
  df$small_biotech_oncology <- as.integer(df$sponsor_type == 'small_biotech' & df$condition_group == 'oncology')
  txt <- tolower(df$brief_title)
  df$title_extension <- as.integer(grepl('extension|registry|long term', txt))
  df
}
choose_threshold <- function(y, p) {
  grid <- seq(0.08, 0.92, by = 0.01)
  rate <- sapply(grid, function(cut) mean(p >= cut))
  cand <- grid[rate >= 0.27 & rate <= 0.33]
  if (length(cand) == 0) cand <- grid
  scores <- sapply(cand, function(cut) {
    lab <- as.integer(p >= cut)
    (mean(lab[y == 1] == 1) + mean(lab[y == 0] == 0)) / 2
  })
  cand[which.max(scores)]
}
positive_prob <- function(mat) {
  if ('1' %in% colnames(mat)) as.numeric(mat[, '1']) else as.numeric(mat[, ncol(mat)])
}
blend <- function(model, tree, df) {
  pmin(0.995, pmax(0.005, 0.85 * as.numeric(predict(model, newdata = df, type = 'response')) +
    0.15 * positive_prob(predict(tree, newdata = df, type = 'prob'))))
}
train_e <- engineer(train)
valid_e <- engineer(valid)
test_e <- engineer(test)
features <- c('condition_group', 'sponsor_type', 'phase', 'log_enrollment', 'log_sites', 'sites_missing', 'duration_months', 'eligibility_word_count', 'country_count', 'prior_amendment_count', 'rare_disease', 'gene_therapy', 'dur_site_mismatch', 'gene_eligibility', 'small_biotech_oncology', 'title_extension')
form <- as.formula(paste(target, '~', paste(features, collapse = ' + ')))
valid_model <- glm(form, data = train_e, family = binomial())
valid_tree <- rpart::rpart(form, data = train_e, method = 'class', control = rpart::rpart.control(cp = 0.006, minbucket = 20))
valid_prob <- blend(valid_model, valid_tree, valid_e)
train_prob <- blend(valid_model, valid_tree, train_e)
valid_cut <- choose_threshold(train[[target]], train_prob)
fit_rows <- rbind(train, valid)
fit_e <- engineer(fit_rows)
final_model <- glm(form, data = fit_e, family = binomial())
final_tree <- rpart::rpart(form, data = fit_e, method = 'class', control = rpart::rpart.control(cp = 0.006, minbucket = 20))
test_prob <- blend(final_model, final_tree, test_e)
fit_prob <- blend(final_model, final_tree, fit_e)
final_cut <- choose_threshold(fit_rows[[target]], fit_prob)
preds <- data.frame(row_id = test$row_id, pred_label = as.integer(test_prob >= final_cut), pred_proba_positive = test_prob)
preds <- preds[order(preds$row_id), ]
write.csv(preds, '/app/output/predictions.csv', row.names = FALSE)
vp <- data.frame(row_id = valid$row_id, pred_label = as.integer(valid_prob >= valid_cut), pred_proba_positive = valid_prob)
vp <- vp[order(vp$row_id), ]
write.csv(vp, '/app/output/validation_predictions.csv', row.names = FALSE)
valid_lab <- as.integer(valid_prob >= valid_cut)
valid_ba <- (mean(valid_lab[valid[[target]] == 1] == 1) + mean(valid_lab[valid[[target]] == 0] == 0)) / 2
rare_valid <- valid$rare_disease == 1
valid_rare_ba <- (mean(valid_lab[rare_valid & valid[[target]] == 1] == 1) + mean(valid_lab[rare_valid & valid[[target]] == 0] == 0)) / 2
metrics <- list(n_train = nrow(fit_rows), n_test = nrow(test), primary_metric_value = auc_rank(valid[[target]], valid_prob), validation_balanced_accuracy = valid_ba, validation_rare_disease_balanced_accuracy = valid_rare_ba, validation_brier = brier(valid[[target]], valid_prob), predicted_positive_rate = mean(preds$pred_label == 1), model_family = 'logistic and rpart probability blend with temporal refit', missing_value_strategy = 'median site imputation with missingness indicator', text_feature_strategy = 'case-insensitive title-derived indicators', final_fit_rows = nrow(fit_rows), temporal_split_year = 2025)
write_json_file(metrics, '/app/output/metrics.json')
