export const setup = () => {
  // Set timezone to America/Havana (GMT-04:00) for consistent snapshot testing across all environments.
  // This timezone is intentionally different from UTC and common dev machine timezones
  // to catch timezone-related bugs in date formatting.
  // Note: This must also be set in package.json test scripts (TZ=America/Havana) using cross-env,
  // as setting process.env.TZ after Node.js has started doesn't affect Date object timezone handling.
  process.env.TZ = "America/Havana"
}
