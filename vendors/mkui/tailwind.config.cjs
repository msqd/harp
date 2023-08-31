const colors = require('tailwindcss/colors')

/** @type {import('tailwindcss').Config} */
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
                50: "#e8ebfb",
                100:"#c4ccf6",
                200: "#9cabf0",
                300: "#7089ea",
                400: "#4a6ee5",
                500: "#0f54df",
                600: '#034bd4',
                700: "#0041c7",
                800: "#0036bc",
                900: "#0022a5",
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
                '90%': '90%',
            },
            maxHeight: {
                "11/12": "91.666667vh",
            },
        },
    },
    plugins: [
        require('@tailwindcss/forms'),
    ],
}
