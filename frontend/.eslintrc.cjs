module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-essential',
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    parser: {
      js: 'espree',
    },
    ecmaVersion: 2022,
    sourceType: 'module',
    extraFileExtensions: ['.vue'],
  },
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/html-self-closing': 'off',
    'vue/max-attributes-per-line': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/attributes-order': 'off',
    'vue/require-explicit-emits': 'off',
    'vue/no-v-html': 'off',
    'no-undef': 'off',
    'no-unused-vars': 'off',
    'no-console': 'off',
  },
  ignorePatterns: [
    'dist',
    'node_modules',
    'backend',
  ],
};
