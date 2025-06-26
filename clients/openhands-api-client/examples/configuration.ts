/**
 * Configuration and Settings Example for OpenHands API Client
 *
 * This example demonstrates how to work with server configuration,
 * settings, and various API options.
 */

import {
  getConfigApiOptionsConfigGet,
  getLitellmModelsApiOptionsModelsGet,
  getAgentsApiOptionsAgentsGet,
  getSecurityAnalyzersApiOptionsSecurityAnalyzersGet,
  loadSettingsApiSettingsGet,
  storeSettingsApiSettingsPost,
  resetSettingsApiResetSettingsPost,
  loadCustomSecretsNamesApiSecretsGet,
  createCustomSecretApiSecretsPost,
  getUserApiUserInfoGet,
  getServerInfoServerInfoGet,
  aliveAliveGet,
  healthHealthGet,
} from '../src/index';

// Configuration
const BASE_URL = 'http://localhost:3000';
const API_CONFIG = {
  baseUrl: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
};

async function configurationExample() {
  console.log('⚙️  OpenHands API Client - Configuration Example\n');

  try {
    // 1. Check if server is alive
    console.log('💓 Checking server health...');
    try {
      const aliveResponse = await aliveAliveGet(API_CONFIG);
      console.log('Server alive:', aliveResponse.data);
    } catch (error) {
      console.log('Server might not be running');
      return;
    }

    // 2. Get health status
    console.log('\n🏥 Getting health status...');
    const healthResponse = await healthHealthGet(API_CONFIG);
    console.log('Health status:', healthResponse.data);

    // 3. Get server info
    console.log('\n📋 Getting server information...');
    const serverInfo = await getServerInfoServerInfoGet(API_CONFIG);
    console.log('Server info:', serverInfo.data);

    // 4. Get current configuration
    console.log('\n⚙️  Getting server configuration...');
    const config = await getConfigApiOptionsConfigGet(API_CONFIG);
    console.log('Configuration:', config.data);

    // 5. Get available models
    console.log('\n🤖 Getting available models...');
    const models = await getLitellmModelsApiOptionsModelsGet(API_CONFIG);
    if (models.data && Array.isArray(models.data)) {
      console.log(`Found ${models.data.length} models:`);
      console.log('First 10 models:', models.data.slice(0, 10));
    }

    // 6. Get available agents
    console.log('\n🧠 Getting available agents...');
    const agents = await getAgentsApiOptionsAgentsGet(API_CONFIG);
    console.log('Available agents:', agents.data);

    // 7. Get security analyzers
    console.log('\n🔒 Getting security analyzers...');
    const securityAnalyzers = await getSecurityAnalyzersApiOptionsSecurityAnalyzersGet(API_CONFIG);
    console.log('Security analyzers:', securityAnalyzers.data);

    console.log('\n✅ Configuration example completed!');

  } catch (error) {
    console.error('❌ Error in configuration example:', error);
  }
}

async function settingsExample() {
  console.log('🛠️  OpenHands API Client - Settings Example\n');

  try {
    // 1. Load current settings
    console.log('📖 Loading current settings...');
    const currentSettings = await loadSettingsApiSettingsGet(API_CONFIG);
    console.log('Current settings:', currentSettings.data);

    // 2. Update settings (example)
    console.log('\n💾 Updating settings...');
    const newSettings = {
      default_agent: 'CodeActAgent',
      default_model: 'gpt-4o-mini',
      language: 'en',
      confirmation_mode: false,
      security_analyzer: null,
      // Add other settings as needed
    };

    try {
      const updateResult = await storeSettingsApiSettingsPost({
        ...API_CONFIG,
        body: newSettings
      });
      console.log('Settings updated:', updateResult.data);
    } catch (error) {
      console.log('Settings update failed (may not be supported):', error);
    }

    // 3. Load settings again to see changes
    console.log('\n🔄 Reloading settings...');
    const updatedSettings = await loadSettingsApiSettingsGet(API_CONFIG);
    console.log('Updated settings:', updatedSettings.data);

    console.log('\n✅ Settings example completed!');

  } catch (error) {
    console.error('❌ Error in settings example:', error);
  }
}

async function secretsExample() {
  console.log('🔐 OpenHands API Client - Secrets Management Example\n');

  try {
    // 1. Load custom secret names
    console.log('📋 Loading custom secret names...');
    const secretNames = await loadCustomSecretsNamesApiSecretsGet(API_CONFIG);
    console.log('Custom secrets:', secretNames.data);

    // 2. Create a custom secret (example - be careful with real secrets!)
    console.log('\n🔑 Creating a custom secret...');
    try {
      const secretResult = await createCustomSecretApiSecretsPost({
        ...API_CONFIG,
        body: {
          name: 'EXAMPLE_API_KEY',
          value: 'example-secret-value-123',
          description: 'Example API key for demonstration'
        }
      });
      console.log('Secret created:', secretResult.data);
    } catch (error) {
      console.log('Secret creation failed (may already exist or not supported)');
    }

    // 3. Reload secret names
    console.log('\n🔄 Reloading secret names...');
    const updatedSecrets = await loadCustomSecretsNamesApiSecretsGet(API_CONFIG);
    console.log('Updated secrets list:', updatedSecrets.data);

    console.log('\n✅ Secrets example completed!');

  } catch (error) {
    console.error('❌ Error in secrets example:', error);
  }
}

async function userInfoExample() {
  console.log('👤 OpenHands API Client - User Information Example\n');

  try {
    // Get user information
    console.log('📋 Getting user information...');
    const userInfo = await getUserApiUserInfoGet(API_CONFIG);
    console.log('User info:', userInfo.data);

    console.log('\n✅ User info example completed!');

  } catch (error) {
    console.error('❌ Error in user info example:', error);
  }
}

// Comprehensive configuration check
async function comprehensiveConfigCheck() {
  console.log('🔍 OpenHands API Client - Comprehensive Configuration Check\n');

  const checks = [
    { name: 'Server Alive', func: () => aliveAliveGet(API_CONFIG) },
    { name: 'Health Check', func: () => healthHealthGet(API_CONFIG) },
    { name: 'Server Info', func: () => getServerInfoServerInfoGet(API_CONFIG) },
    { name: 'Configuration', func: () => getConfigApiOptionsConfigGet(API_CONFIG) },
    { name: 'Models', func: () => getLitellmModelsApiOptionsModelsGet(API_CONFIG) },
    { name: 'Agents', func: () => getAgentsApiOptionsAgentsGet(API_CONFIG) },
    { name: 'Security Analyzers', func: () => getSecurityAnalyzersApiOptionsSecurityAnalyzersGet(API_CONFIG) },
    { name: 'Settings', func: () => loadSettingsApiSettingsGet(API_CONFIG) },
    { name: 'Secrets', func: () => loadCustomSecretsNamesApiSecretsGet(API_CONFIG) },
    { name: 'User Info', func: () => getUserApiUserInfoGet(API_CONFIG) },
  ];

  for (const check of checks) {
    try {
      console.log(`🔄 Checking ${check.name}...`);
      const result = await check.func();
      console.log(`✅ ${check.name}: OK`);

      // Log some basic info about the response
      if (result.data) {
        if (Array.isArray(result.data)) {
          console.log(`   - Array with ${result.data.length} items`);
        } else if (typeof result.data === 'object') {
          console.log(`   - Object with keys: ${Object.keys(result.data).join(', ')}`);
        } else {
          console.log(`   - Value: ${result.data}`);
        }
      }
    } catch (error) {
      console.log(`❌ ${check.name}: Failed`);
      console.log(`   - Error: ${error}`);
    }
    console.log(''); // Empty line for readability
  }

  console.log('✅ Comprehensive configuration check completed!');
}

export {
  configurationExample,
  settingsExample,
  secretsExample,
  userInfoExample,
  comprehensiveConfigCheck
};

// Run example if called directly
if (typeof window === 'undefined') {
  const examples = {
    '1': configurationExample,
    '2': settingsExample,
    '3': secretsExample,
    '4': userInfoExample,
    '5': comprehensiveConfigCheck
  };

  console.log('Available examples:');
  console.log('1. Configuration Example');
  console.log('2. Settings Example');
  console.log('3. Secrets Example');
  console.log('4. User Info Example');
  console.log('5. Comprehensive Configuration Check');

  const choice = '5'; // Default to comprehensive check
  const exampleFunc = examples[choice as keyof typeof examples] || comprehensiveConfigCheck;

  exampleFunc().catch(console.error);
}
