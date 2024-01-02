const colors = require("tailwindcss/colors")

/** @type {import("tailwindcss").Config} */
module.exports = {
  content: ["./src/**/*.{html,js,jsx,ts,tsx}"],
  theme: {
    colors: {
      inherit: colors.inherit,
      current: colors.current,
      transparent: colors.transparent,
      black: colors.black,
      white: colors.white,
      primary: {
        50: "#e2f6fe",
        100: "#b5e8fc",
        200: "#85d9fb",
        300: "#56caf9",
        400: "#34bef8",
        500: "#1ab2f8",
        600: "#15a4e9",
        700: "#0f91d5",
        800: "#0d7fc1",
        900: "#065f9f",
      },
      secondary: colors.slate,
      gray: colors.gray,
      red: colors.red,
      yellow: colors.yellow,
      green: colors.green,
      blue: colors.blue,
      orange: colors.orange,
      purple: colors.purple,
    },
    extend: {
      maxWidth: {
        "90%": "90%",
      },
      maxHeight: {
        "11/12": "91.666667vh",
      },

    },
  },
  plugins: [
    require("@tailwindcss/forms"),
    require("@tailwindcss/typography"),
  ],
}
