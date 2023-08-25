/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        electric: "#db00ff",
        ribbon: "#0047ff",
      },
      maxWidth: {
        '90%': '90%',
      },
      maxHeight: {
        "11/12": "91.666667vh",
      },
    },
  },
  plugins: [],
}
