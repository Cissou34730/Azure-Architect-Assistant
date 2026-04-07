// eslint.config.js (root, ESM)

import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import checkFile from "eslint-plugin-check-file";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import oxlint from "eslint-plugin-oxlint";
import { fileURLToPath } from "node:url";

const oxlintConfigPath = fileURLToPath(new URL("./.oxlintrc.json", import.meta.url));

const strictTsCoreRules = {
  // Disable core versions when TS versions are used
  "no-unused-vars": "off",
  "no-unused-expressions": "off",

  // TypeScript: strict unused checks
  "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
  "@typescript-eslint/no-unused-expressions": "error",

  // Owned by Oxlint to avoid duplicate checks in ESLint.
  "@typescript-eslint/no-explicit-any": "off",
  "@typescript-eslint/no-unsafe-assignment": "off",
  "@typescript-eslint/no-unsafe-member-access": "off",
  "@typescript-eslint/no-unsafe-call": "off",
  "@typescript-eslint/no-unsafe-argument": "off",
  "@typescript-eslint/no-unsafe-return": "off",
  "@typescript-eslint/no-non-null-assertion": "off",
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
  "@typescript-eslint/strict-boolean-expressions": "off",
  "@typescript-eslint/restrict-plus-operands": "off",
  "@typescript-eslint/restrict-template-expressions": "off",
  "@typescript-eslint/no-floating-promises": "off",
  "@typescript-eslint/switch-exhaustiveness-check": "off",

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
    // Allow any format for properties that require quotes (e.g. "Content-Type" HTTP headers)
    {
      selector: ["objectLiteralProperty", "typeProperty"],
      modifiers: ["requiresQuotes"],
      format: null,
    },
    // Allow snake_case for API-boundary properties & methods (wire format from Python/FastAPI backend)
    {
      selector: ["typeProperty", "objectLiteralProperty", "objectLiteralMethod"],
      filter: { regex: "^[a-z][a-z0-9]*(_[a-z0-9]+)+$", match: true },
      format: null,
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
  "react/jsx-no-useless-fragment": "off",
  "react/self-closing-comp": "off",
  "react/no-array-index-key": "warn",
  "react/prop-types": "off",
  "react/function-component-definition": [
    "error",
    {
      namedComponents: "function-declaration",
      unnamedComponents: "arrow-function",
    },
  ],
};

const frontendRootCompatibilityPatterns = [
  "../../../services/*",
  "../../../../services/*",
  "../../../../../services/*",
  "../../../hooks/*",
  "../../../../hooks/*",
  "../../../../../hooks/*",
  "../../../config/*",
  "../../../../config/*",
  "../../../../../config/*",
  "../../../utils/*",
  "../../../../utils/*",
  "../../../../../utils/*",
];

const frontendRootTypeShimPatterns = [
  "../../types/api",
  "../../../types/api",
  "../../../../types/api",
  "../../../../../types/api",
  "../../../types/agent",
  "../../../../types/agent",
  "../../../../../types/agent",
  "../../../types/ingestion",
  "../../../../types/ingestion",
  "../../../../../types/ingestion",
  "../../../types/api-kb",
  "../../../../types/api-kb",
  "../../../../../types/api-kb",
  "../../../types/api-diagrams",
  "../../../../types/api-diagrams",
  "../../../../../types/api-diagrams",
];

export default [
  // 1. Global ignores
  {
    ignores: [
      "dist",
      "**/dist",
      "eslint.config.js",
      "**/eslint.config.js",
      "**/vite.config.ts",
      "node_modules",
      "**/node_modules",
      "**/*.config.js",
      "backend/**",
      "archive/**",
      "backups/**",
      "ShouldBeRemoved/**",
      ".github/**",
      "*.py",
      "**/*.py",
      "**/*.json",
      "**/*.md",
    ],
  },

  // 2. Base JS recommended config (for any remaining JS files)
  {
    files: ["**/*.js", "**/*.mjs", "**/*.cjs"],
    ...js.configs.recommended,
  },

  // 3. TypeScript type-checked configs (applies to all TS/TSX files)
  ...tseslint.configs.strictTypeChecked.map((config) => ({
    ...config,
    files: ["**/*.ts", "**/*.tsx"],
  })),
  ...tseslint.configs.stylisticTypeChecked.map((config) => ({
    ...config,
    files: ["**/*.ts", "**/*.tsx"],
  })),

  // 4. Language options for TypeScript files
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: true,
        tsconfigRootDir: import.meta.dirname,
      },
      globals: {
        ...globals.browser,
        ...globals.es2020,
      },
    },
  },

  // 3. TS files (.ts) – stricter modularity
  {
    files: ["**/*.ts"],

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
    files: ["**/*.tsx"],

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
  },

  // 5. Frontend architecture baseline – make dependency drift visible before Phase 2 moves.
  {
    files: ["frontend/src/features/**/*.ts", "frontend/src/features/**/*.tsx"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: [
                ...frontendRootCompatibilityPatterns,
                ...frontendRootTypeShimPatterns,
              ],
              message:
                "Feature modules must not import root compatibility shims. Import from canonical feature or shared modules instead.",
            },
          ],
        },
      ],
    },
  },

  {
    files: [
      "frontend/src/features/projects/**/*.ts",
      "frontend/src/features/projects/**/*.tsx",
      "frontend/src/features/knowledge/components/**/*.ts",
      "frontend/src/features/knowledge/components/**/*.tsx",
      "frontend/src/__tests__/features/projects/**/*.ts",
      "frontend/src/__tests__/features/projects/**/*.tsx",
    ],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: [
                ...frontendRootCompatibilityPatterns,
                ...frontendRootTypeShimPatterns,
              ],
              message:
                "Feature modules must not import root compatibility shims. Import from canonical feature or shared modules instead.",
            },
            {
              group: frontendRootTypeShimPatterns,
              message:
                "Feature modules must not import the removed root api compatibility shim.",
            },
          ],
        },
      ],
    },
  },

  {
    files: [
      "frontend/src/shared/**/*.ts",
      "frontend/src/shared/**/*.tsx",
      "frontend/src/services/**/*.ts",
      "frontend/src/services/**/*.tsx",
      "frontend/src/hooks/**/*.ts",
      "frontend/src/hooks/**/*.tsx",
      "frontend/src/types/**/*.ts",
      "frontend/src/types/**/*.tsx",
    ],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: [
                "../features/*",
                "../../features/*",
                "../../../features/*",
              ],
              message:
                "Top-level shared frontend modules must not import from features.",
            },
          ],
        },
      ],
    },
  },

  // 6. Test file overrides — relax rules that conflict with test patterns
  {
    files: [
      "**/__tests__/**/*.ts",
      "**/__tests__/**/*.tsx",
      "**/*.test.ts",
      "**/*.test.tsx",
    ],
    rules: {
      // Mock functions (vi.fn stubs, jest-style) are intentionally empty
      "@typescript-eslint/no-empty-function": "off",
      // Destructuring mocked methods from an object is idiomatic in tests
      "@typescript-eslint/unbound-method": "off",
      // describe() / it() callbacks are inherently long
      "max-lines-per-function": "off",
      "max-lines": "off",
      // Type assertions are standard when constructing typed test fixtures
      "no-restricted-syntax": "off",
      "@typescript-eslint/no-unsafe-type-assertion": "off",
      // unknown is acceptable for mock boundary values in tests
      "@typescript-eslint/no-restricted-types": "off",
      // Test helpers may be async without an explicit await (e.g. timers)
      "@typescript-eslint/require-await": "off",
    },
  },

  // 7. Disable duplicate ESLint rules that are enforced by Oxlint.
  ...oxlint.buildFromOxlintConfigFile(oxlintConfigPath),
];
