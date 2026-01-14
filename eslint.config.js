// eslint.config.js (root, ESM)

import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import checkFile from "eslint-plugin-check-file";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";

const strictTsCoreRules = {
  // Disable core versions when TS versions are used
  "no-unused-vars": "off",
  "no-unused-expressions": "off",

  // TypeScript: strict unused checks
  "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
  "@typescript-eslint/no-unused-expressions": "error",

  // TypeScript: no any, no unsafe operations
  "@typescript-eslint/no-explicit-any": [
    "error",
    {
      fixToUnknown: true,
      ignoreRestArgs: false,
    },
  ],
  "@typescript-eslint/no-unsafe-assignment": "error",
  "@typescript-eslint/no-unsafe-member-access": "error",
  "@typescript-eslint/no-unsafe-call": "error",
  "@typescript-eslint/no-unsafe-argument": "error",
  "@typescript-eslint/no-unsafe-return": "error",
  "@typescript-eslint/no-non-null-assertion": "error",
  "@typescript-eslint/consistent-type-definitions": ["error", "interface"],

  // TypeScript: ban unsafe and unnecessary assertions
  "@typescript-eslint/no-unsafe-type-assertion": "error",
  "@typescript-eslint/no-unnecessary-type-assertion": "error",

  // Effectively forbid all type assertions (`as`, `<Type>`)
  "no-restricted-syntax": [
    "error",
    {
      selector: "TSAsExpression",
      message:
        "Do not use 'as' assertions. Prefer precise types or type guards.",
    },
    {
      selector: "TSTypeAssertion",
      message:
        "Do not use '<Type>' assertions. Prefer precise types or type guards.",
    },
  ],

  // Hardened boolean, arithmetic, template usage
  "@typescript-eslint/strict-boolean-expressions": [
    "error",
    {
      allowAny: false,
      allowNumber: false,
      allowString: false,
      allowNullableBoolean: true,
      allowNullableEnum: false,
      allowNullableNumber: false,
      allowNullableObject: false,
      allowNullableString: false,
      allowRuleToRunWithoutStrictNullChecksIKnowWhatIAmDoing: false,
    },
  ],
  "@typescript-eslint/restrict-plus-operands": [
    "error",
    {
      allowAny: false,
      allowBoolean: false,
      allowNullish: false,
      allowNumberAndString: false,
      allowRegExp: false,
      skipCompoundAssignments: false,
    },
  ],
  "@typescript-eslint/restrict-template-expressions": [
    "error",
    {
      allowNumber: true,
      allowBoolean: false,
      allowNullish: false,
      allowAny: false,
      allowArray: false,
      allowRegExp: false,
      allowNever: false,
    },
  ],
  "@typescript-eslint/no-floating-promises": "error",
  "@typescript-eslint/switch-exhaustiveness-check": "error",

  // Restrict some types: discourage unknown internally, ban React.FC
  "@typescript-eslint/no-restricted-types": [
    "warn",
    {
      types: {
        unknown: {
          message:
            "Avoid 'unknown' in internal code. Use domain types; reserve 'unknown' for external boundaries (I/O, JSON, external APIs).",
        },
        "React.FC": {
          message:
            "Avoid React.FC; use a named function component with explicit props.",
        },
        "React.FunctionComponent": {
          message:
            "Avoid React.FunctionComponent; use a named function component with explicit props.",
        },
      },
    },
  ],

  // Naming conventions
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
    {
      selector: "import",
      format: ["camelCase", "PascalCase"],
    },
  ],
};

const reactRules = {
  // React + React Hooks recommended rules
  ...reactHooks.configs.recommended.rules,
  ...react.configs.recommended.rules,

  // React-specific refinements
  "react-refresh/only-export-components": [
    "warn",
    { allowConstantExport: true },
  ],
  "react/react-in-jsx-scope": "off",
  "react/no-unknown-property": "off",
  "react/jsx-no-useless-fragment": "error",
  "react/self-closing-comp": "error",
  "react/no-array-index-key": "warn",
  "react/function-component-definition": [
    "error",
    {
      namedComponents: "function-declaration",
      unnamedComponents: "arrow-function",
    },
  ],
};

export default tseslint.config(
  // 1. Global ignores
  {
    ignores: [
      "dist",
      "frontend/dist",
      "eslint.config.js",
      "**/eslint.config.js",
      "vite.config.ts",
      "frontend/vite.config.ts",
    ],
  },

  // 2. Base JS/TS recommended configs
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,

  // 3. TS files (.ts) – stricter modularity
  {
    files: ["frontend/src/**/*.ts"],

    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
      parserOptions: {
        project: ["./frontend/tsconfig.json", "./frontend/tsconfig.node.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },

    plugins: {
      "check-file": checkFile,
      // no React needed for plain TS modules
    },

    rules: {
      ...strictTsCoreRules,

      // Complexity / size limits – TS
      complexity: ["error", 10],
      "max-lines": [
        "error",
        { max: 200, skipBlankLines: true, skipComments: true },
      ],
      "max-lines-per-function": [
        "error",
        { max: 50, skipBlankLines: true, skipComments: true },
      ],
      "max-params": ["error", { max: 3 }],

      // File naming conventions
      "check-file/filename-naming-convention": [
        "error",
        {
          "**/*.{ts}": "KEBAB_CASE",
        },
        { ignoreMiddleExtensions: true },
      ],

      // Promises in handlers/effects (applies in general too)
      "@typescript-eslint/no-misused-promises": [
        "error",
        { checksVoidReturn: { attributes: false } },
      ],
    },
  },

  // 4. TSX files (.tsx) – allow more lines for readability
  {
    files: ["frontend/src/**/*.tsx"],

    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
      parserOptions: {
        project: ["./frontend/tsconfig.json", "./frontend/tsconfig.node.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },

    plugins: {
      "check-file": checkFile,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      react,
    },

    settings: {
      react: { version: "detect" },
    },

    rules: {
      ...strictTsCoreRules,
      ...reactRules,

      // Complexity / size limits – TSX
      complexity: ["error", 10],
      "max-lines": [
        "error",
        { max: 300, skipBlankLines: true, skipComments: true },
      ],
      "max-lines-per-function": [
        "error",
        { max: 100, skipBlankLines: true, skipComments: true },
      ],
      "max-params": ["error", { max: 3 }],

      // File naming conventions
      "check-file/filename-naming-convention": [
        "error",
        {
          "**/*.{tsx}": "PASCAL_CASE",
        },
        { ignoreMiddleExtensions: true },
      ],

      "@typescript-eslint/no-misused-promises": [
        "error",
        { checksVoidReturn: { attributes: false } },
      ],
    },
  }
);
