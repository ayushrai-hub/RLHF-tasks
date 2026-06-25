export interface PipelineContext {
  dbPath: string;
  dossierPath: string;
  outputPath: string;
  verbose: boolean;
}

export interface PipelineStep<TIn, TOut> {
  readonly name: string;
  run(input: TIn, ctx: PipelineContext): Promise<TOut> | TOut;
}
