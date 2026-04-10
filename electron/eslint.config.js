const globals = require("globals")

module.exports = [
  // Ignore directories that should not be linted
  {
    ignores: ["node_modules/", "dist/", "out/"]
  },
  // Lint all .js files in the project
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "commonjs",
      globals: {
        ...globals.node,
        ...globals.browser
      }
    },
    rules: {
      // Error-level rules — catch real bugs
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-undef": "error",
      "no-redeclare": "error",
      "no-dupe-keys": "error",
      "no-duplicate-case": "error",
      "no-empty": "error",
      "no-extra-semi": "error",
      "no-unreachable": "error",
      "no-constant-condition": "warn",
      "no-debugger": "warn",
      "no-dupe-args": "error",
      "no-func-assign": "error",
      "no-inner-declarations": "error",
      "no-irregular-whitespace": "error",
      "no-sparse-arrays": "warn",
      "no-unexpected-multiline": "error",
      "valid-typeof": "error",

      // Style rules — warnings only
      "no-console": "off",
      "no-multiple-empty-lines": ["warn", { max: 2 }],
      "no-trailing-spaces": "warn",
      "semi": ["warn", "never"],
      "quotes": ["warn", "double", { avoidEscape: true }],
      "indent": ["warn", 2, { SwitchCase: 1 }],
      "comma-dangle": ["warn", "never"],
      "eqeqeq": ["warn", "smart"],
      "curly": ["warn", "multi-line"],
      "no-var": "off"
    }
  }
]