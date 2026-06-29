from pathlib import Path

APP = Path("/app")
JAR = str(APP / "java/build/libs/skct-pipeline-1.0.0.jar")
CORPUS = APP / "feature_corpus/sklearn_pipeline_column_transform_corpus.md"
BUNDLE = APP / "fixtures/bundles/pipeline_alpha_v3.json"
BETA = APP / "fixtures/bundles/pipeline_beta_v1.json"
