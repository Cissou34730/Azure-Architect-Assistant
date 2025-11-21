type LogLevel = "error" | "warn" | "info";

const LEVEL_ORDER: Record<LogLevel, number> = {
  error: 0,
  warn: 1,
  info: 2,
};

function normalizeLevel(value?: string): LogLevel {
  if (!value) return "info";
  const normalized = value.toLowerCase();
  if (normalized === "warning") return "warn";
  if (normalized === "error" || normalized === "warn" || normalized === "info") {
    return normalized as LogLevel;
  }
  return "info";
}

let currentLevel: LogLevel = normalizeLevel(process.env.LOG_LEVEL);

export function setLogLevel(level: LogLevel): void {
  currentLevel = level;
}

export function getLogLevel(): LogLevel {
  return currentLevel;
}

export function configureLoggerFromEnv(env: NodeJS.ProcessEnv = process.env): void {
  currentLevel = normalizeLevel(env.LOG_LEVEL);
}

export class Logger {
  constructor(private scope?: string) {}

  child(scope: string): Logger {
    return new Logger(scope);
  }

  info(message: string, meta?: unknown): void {
    this.log("info", message, meta);
  }

  warn(message: string, meta?: unknown): void {
    this.log("warn", message, meta);
  }

  error(message: string, meta?: unknown): void {
    this.log("error", message, meta);
  }

  log(level: LogLevel, message: string, meta?: unknown): void {
    if (!this.shouldLog(level)) return;
    const payload = this.format(level, message);

    if (meta !== undefined) {
      this.logToConsole(level, payload, meta);
      return;
    }

    this.logToConsole(level, payload);
  }

  private shouldLog(level: LogLevel): boolean {
    return LEVEL_ORDER[level] <= LEVEL_ORDER[currentLevel];
  }

  private format(level: LogLevel, message: string): string {
    const timestamp = new Date().toISOString();
    const scopePart = this.scope ? ` [${this.scope}]` : "";
    return `${timestamp} ${level.toUpperCase()}${scopePart} ${message}`;
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private logToConsole(level: LogLevel, payload: string, meta?: any): void {
    if (level === "error") {
      meta !== undefined ? console.error(payload, meta) : console.error(payload);
    } else if (level === "warn") {
      meta !== undefined ? console.warn(payload, meta) : console.warn(payload);
    } else {
      meta !== undefined ? console.log(payload, meta) : console.log(payload);
    }
  }
}

export const logger = new Logger();
