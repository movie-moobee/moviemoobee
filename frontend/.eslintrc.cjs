module.exports = {
  root: true,
  ignorePatterns: ["dist/", "node_modules/"],
  env: { browser: true, es2022: true, node: true },
  extends: ["eslint:recommended", "plugin:vue/vue3-recommended"],
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  rules: { "vue/multi-word-component-names": "off" },
};
