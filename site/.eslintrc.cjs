/**
 * Public landing site ESLint configuration.
 *
 * The site is a small Vite/React TypeScript app and intentionally keeps its
 * lint surface local to `site/src`; the dashboard's flat configs do not apply
 * here.  Keep the rules strict enough to catch broken hooks and unused code
 * while allowing the existing component style (single quotes/semicolons are a
 * formatter concern, not a correctness rule).
 */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
  ],
  settings: {
    react: { version: 'detect' },
  },
  rules: {
    'no-console': 'warn',
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-unused-vars': ['error', {
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_',
      caughtErrorsIgnorePattern: '^_',
    }],
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    // Several animation modules intentionally export both components and
    // motion variants/hooks; the rule is for dev HMR ergonomics, not a
    // correctness check, and would make the site's max-warnings=0 lint noisy.
    'react-refresh/only-export-components': 'off',
  },
  overrides: [
    {
      files: ['src/**/*.test.{ts,tsx}'],
      rules: {
        'react-refresh/only-export-components': 'off',
      },
    },
  ],
};
