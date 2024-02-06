const nextJest = require("next/jest")

const babelConfigStyledComponents = {
  presets: [["next/babel", { "preset-react": { runtime: "automatic" } }]],
  plugins: ["babel-plugin-macros", ["babel-plugin-styled-components", { ssr: true }]],
}

/** @type {import('ts-jest').JestConfigWithTsJest} */
const customJestConfig = {
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testEnvironment: "jest-environment-jsdom",
  moduleNameMapper: {
    "^@/components/(.*)$": "<rootDir>/components/$1",
  },
  transform: {
    "^.+\\.(js|jsx|ts|tsx|mjs)$": ["babel-jest", babelConfigStyledComponents],
  },
  collectCoverageFrom: [
    "src/**/*.{js,jsx,ts,tsx}",
    "!<rootDir>/node_modules/",
    "!<rootDir>/**/*.stories.{js,jsx,ts,tsx}",
  ],
  coverageDirectory: "<rootDir>/coverage",
  testPathIgnorePatterns: ["<rootDir>/tests/"],
  coverageReporters: ["html", "text"],
}

const createJestConfig = nextJest({ dir: "./" })

module.exports = createJestConfig(customJestConfig)
