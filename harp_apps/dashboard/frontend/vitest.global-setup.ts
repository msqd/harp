export const setup = () => {
  // Set timezone to Cuba (GMT-04:00) for consistent snapshot testing across all environments.
  // This timezone is intentionally different from UTC and common dev machine timezones
  // to catch timezone-related bugs in date formatting.
  // Note: This must also be set in CI environment variables (TZ=Cuba) for container-level
  // enforcement, as some CI environments don't properly propagate process.env.TZ.
  process.env.TZ = "Cuba"
}
