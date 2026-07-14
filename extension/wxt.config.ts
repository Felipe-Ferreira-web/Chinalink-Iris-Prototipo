import { defineConfig } from 'wxt';

export default defineConfig({
  manifest: {
    name: 'Iris - Extração de Contato de Fornecedor',
    description: 'Revela e extrai o contato do fornecedor na página, repassando para o server',
    version: '0.1.0',
    permissions: ['storage', 'activeTab'],
    host_permissions: [
      '*://*.alibaba.com/*',
      'http://localhost:8000/*',
    ],
    browser_specific_settings: {
      gecko: {
        id: 'iris@chinalinktrading.com',
      },
    },
  },
});
