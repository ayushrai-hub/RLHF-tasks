import { PipelineContext, PipelineStep } from './PipelineStep.js';
import { logger } from '../logger.js';

/**
 * Linear processing pipeline. Each step receives the output of the previous step.
 * Use Pipeline.add() to register steps in order, then Pipeline.run() to execute.
 */
export class Pipeline<TInitial, TFinal> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private readonly steps: PipelineStep<any, any>[] = [];

  add<TIn, TOut>(step: PipelineStep<TIn, TOut>): Pipeline<TInitial, TOut> {
    this.steps.push(step);
    return this as unknown as Pipeline<TInitial, TOut>;
  }

  async run(initial: TInitial, ctx: PipelineContext): Promise<TFinal> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let value: any = initial;
    for (const step of this.steps) {
      logger.info(`Pipeline: running step "${step.name}"`);
      value = await Promise.resolve(step.run(value, ctx));
    }
    return value as TFinal;
  }
}
