import reactRefresh from 'eslint-plugin-react-refresh';

export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'src/**/*.ts', 'src/**/*.tsx', '**/*.d.ts'],
  },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      globals: {
        process: 'readonly',
      },
    },
    plugins: {
      'react-refresh': reactRefresh,
    },
    rules: {
      'no-undef': 'error',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'react-refresh/only-export-components': 'warn',
    },
  },
];