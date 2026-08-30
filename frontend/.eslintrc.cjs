module.exports = {
  env: { browser: true, es2021: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaFeatures: { jsx: true },
    ecmaVersion: 12,
    sourceType: 'module',
  },
  settings: { react: { version: '18.2' } },
  plugins: ['react', '@typescript-eslint', 'react-hooks'],
  rules: { 'react/react-in-jsx-scope': 'off' },
};
