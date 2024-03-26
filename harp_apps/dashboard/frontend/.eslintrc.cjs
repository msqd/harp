/* eslint-env node */

module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  ignorePatterns: ["**/tests/*", "**/*.test.ts", "**/*.test.tsx"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:@typescript-eslint/recommended-requiring-type-checking",
    "plugin:react-hooks/recommended",
    "plugin:import/recommended",
    "plugin:import/typescript",
    "plugin:prettier/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    project: true,
    tsconfigRootDir: __dirname,
  },
  plugins: ["json", "autofix", "react-refresh"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-non-null-assertion": "off",
    "import/order": [
      "warn",
      {
        alphabetize: {
          order: "asc",
          caseInsensitive: false,
        },
        groups: ["builtin", "external", "internal", "sibling", "parent"],
        "newlines-between": "always",
      },
    ],
  },
  settings: {
    "import/internal-regex": "^(mkui|[A-Z])",
    "import/resolver": {
      typescript: true,
      node: true,
    },
  },
}
