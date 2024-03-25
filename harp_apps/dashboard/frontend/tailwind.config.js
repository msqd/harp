const colors = require("tailwindcss/colors")

/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}", "../vendors/mkui/src/**/*.{html,js,jsx,ts,tsx}"],
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
      fontFamily: {
        sans: 'Lato, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"',
      },
      minWidth: {},
      maxWidth: {
        "1/5": "20%",
        "1/3": "33%",
        "2/5": "40%",
        "90%": "90%",
        128: "32rem",
      },
      maxHeight: {
        "11/12": "91.7vh",
      },
      width: {
        128: "32rem",
      },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
}
