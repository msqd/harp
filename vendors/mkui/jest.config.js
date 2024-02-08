const babelConfigEmotion = {
  presets: [
    [
      "@babel/preset-env",
      {
        targets: { node: "current" },
      },
    ],
    [
      "@babel/preset-react",
      {
        runtime: "automatic",
        importSource: "@emotion/react",
      },
    ],
    "@babel/preset-typescript",
  ],
  plugins: ["babel-plugin-macros", "@emotion/babel-plugin"],
}

/** @type {import('ts-jest').JestConfigWithTsJest} */
const customJestConfig = {
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testEnvironment: "jest-environment-jsdom",
  moduleNameMapper: {
    "^@/components/(.*)$": "<rootDir>/src/components/$1",
    "^@/pages/(.*)$": "<rootDir>/src/pages/$1",
  },
  transform: {
    "^.+\\.(js|jsx|ts|tsx|mjs)$": ["babel-jest", babelConfigEmotion],
    "^.+\\.svg$": "<rootDir>/svgTransform.js",
  },

  collectCoverageFrom: [
    "src/**/*.{js,jsx,tsx}",
    "!<rootDir>/node_modules/",
    "!<rootDir>/**/*.stories.{js,jsx,ts,tsx}",
    "!<rootDir>/**/Styles/**/*.{js,jsx,ts,tsx}",
  ],
  coverageDirectory: "<rootDir>/coverage",
  testPathIgnorePatterns: ["<rootDir>/tests/"],
  coverageReporters: ["html", "text"],
}

module.exports = customJestConfig
