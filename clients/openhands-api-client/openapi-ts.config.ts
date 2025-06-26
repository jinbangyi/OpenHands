import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'http://localhost:3000/openapi.json',
  output: 'clients/openhands-api-client/src',
});

// pnpm openapi-ts -f clients/openhands-api-client/openapi-ts.config.ts
