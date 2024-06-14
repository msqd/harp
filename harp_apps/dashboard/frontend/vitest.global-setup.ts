export const setup = () => {
  // Let's tun the test in a timezone that is not UTC nor one of the usual timezones our dev boxes are in
  process.env.TZ = "Cuba"
}
