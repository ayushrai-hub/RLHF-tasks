export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

let currentLevel: LogLevel = 'info';

export function setLogLevel(level: LogLevel): void {
  currentLevel = level;
}

const LEVELS: Record<LogLevel, number> = { debug: 0, info: 1, warn: 2, error: 3 };

function shouldLog(level: LogLevel): boolean {
  return LEVELS[level] >= LEVELS[currentLevel];
}

export const logger = {
  debug: (msg: string, ...args: unknown[]) => shouldLog('debug') && process.stderr.write(`[DEBUG] ${msg} ${args.map(a => JSON.stringify(a)).join(' ')}\n`),
  info: (msg: string, ...args: unknown[]) => shouldLog('info') && process.stderr.write(`[INFO] ${msg} ${args.map(a => JSON.stringify(a)).join(' ')}\n`),
  warn: (msg: string, ...args: unknown[]) => shouldLog('warn') && process.stderr.write(`[WARN] ${msg} ${args.map(a => JSON.stringify(a)).join(' ')}\n`),
  error: (msg: string, ...args: unknown[]) => shouldLog('error') && process.stderr.write(`[ERROR] ${msg} ${args.map(a => JSON.stringify(a)).join(' ')}\n`),
};
