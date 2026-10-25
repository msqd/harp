/* eslint-env node */

module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  ignorePatterns: ["**/tests/*", "**/*.test.ts", "**/*.test.tsx", "src/Models/*.d.ts"],
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
  plugins: ["json", "autofix", "react-refresh", "react"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-non-null-assertion": "off",
    // a link opening a new window must not hand it window.opener, nor our URL as referrer
    "react/jsx-no-target-blank": ["error", { allowReferrer: false, enforceDynamicLinks: "always" }],
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
    react: { linkComponents: [{ name: "Link", linkAttribute: "to" }] },
    "import/internal-regex": "^(mkui|[A-Z])",
    "import/resolver": {
      typescript: true,
      node: true,
    },
  },
}
