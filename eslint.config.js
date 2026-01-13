import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import checkFile from "eslint-plugin-check-file";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";

export default tseslint.config(
  /* 1. Base Ignore Patterns (Global) */
  { ignores: ["dist", "eslint.config.js", "vite.config.ts"] },

  /* 2. Base JS/TS Configurations */
  {
    extends: [
      js.configs.recommended,
      ...tseslint.configs.strictTypeChecked /* 🛡️ The "Hardened" Type Rules */,
      ...tseslint.configs.stylisticTypeChecked,
    ],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        project: ["./tsconfig.json", "./tsconfig.node.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      "check-file": checkFile,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      react,
    },
    /* 3. The Rules (Merged & Hardened) */
    settings: {
      react: { version: "detect" },
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...react.configs.recommended.rules,

      /* 🔴 CRITICAL TYPE SAFETY */
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unsafe-assignment": "error",
      "@typescript-eslint/no-unsafe-member-access": "error",
      "@typescript-eslint/no-unsafe-call": "error",
      "@typescript-eslint/no-unsafe-argument": "error",
      "@typescript-eslint/no-unsafe-return": "error",
      "@typescript-eslint/no-non-null-assertion": "error",
      "@typescript-eslint/consistent-type-definitions": ["error", "interface"],

      /* 🧠 SEMANTIC SMELLS & BLOAT */
      complexity: ["error", 10],
      "max-lines": [
        "error",
        { max: 300, skipBlankLines: true, skipComments: true },
      ],
      "max-lines-per-function": [
        "error",
        { max: 50, skipBlankLines: true, skipComments: true },
      ],
      "max-params": ["error", { max: 3 }],

      /* 📂 ARCHITECTURE (Naming) */
      "check-file/filename-naming-convention": [
        "error",
        {
          "**/*.{tsx}": "PASCAL_CASE",
          "**/*.{ts}": "KEBAB_CASE",
        },
        { ignoreMiddleExtensions: true },
      ],

      /* 🟠 NAMING CONVENTIONS */
      "@typescript-eslint/naming-convention": [
        "error",
        {
          selector: "default",
          format: ["camelCase"],
          leadingUnderscore: "allow",
        },
        {
          selector: "variable",
          format: ["camelCase", "UPPER_CASE"],
        },
        {
          selector: "function",
          format: ["camelCase", "PascalCase"],
        },
        {
          selector: "typeLike",
          format: ["PascalCase"],
        },
      ],

      /* 🛠️ REACT SPECIFICS */
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "react/react-in-jsx-scope": "off",
      "react/no-unknown-property": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-misused-promises": [
        "error",
        { checksVoidReturn: { attributes: false } },
      ],
      "@typescript-eslint/no-unused-expressions": "error",
    },
  }
);
