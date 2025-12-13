import pluginVue from 'eslint-plugin-vue'
import vueTsEslintConfig from '@vue/eslint-config-typescript'

export default [
  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist*/**', '**/out/**', '**/node_modules/**', '**/.vite/**']
  },

  // Apply Vue + TypeScript configs
  ...pluginVue.configs['flat/essential'],
  ...vueTsEslintConfig(),

  // Custom rules
  {
    name: 'app/custom-rules',
    files: ['**/*.{ts,mts,tsx,vue}'],
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/no-explicit-any': 'warn',
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off'
    }
  }
]
