#!/usr/bin/env node

/**
 * Quick test script to verify the OpenHands TypeScript client works
 */

const { createClient } = require('./dist/index.js');

async function quickTest() {
  const client = createClient({
    baseUrl: process.env.OPENHANDS_URL || 'http://localhost:33135',
    apiKey: process.env.OPENHANDS_API_KEY,
    timeout: 10000,
  });

  console.log('Testing OpenHands TypeScript Client...\n');

  try {
    // Test 1: Server alive check
    console.log('🔍 Test 1: Checking if server is alive...');
    const aliveResponse = await client.checkAlive();
    console.log('✅ Result:', aliveResponse);

    // Test 2: Simple command
    console.log('\n🔍 Test 2: Running simple command...');
    const cmdResponse = await client.runCommand('echo "Hello from TypeScript client!"');
    console.log('✅ Command executed successfully');
    console.log('📄 Output:', cmdResponse.content.trim());

    // Test 3: List files
    console.log('\n🔍 Test 3: Listing root directory...');
    const files = await client.listFiles('/');
    console.log('✅ Found', files.length, 'items');
    console.log('📁 First 5 items:', files.slice(0, 5));

    console.log('\n🎉 All tests passed! The TypeScript client is working correctly.');

  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    if (error.status) {
      console.error('HTTP Status:', error.status);
    }
    process.exit(1);
  }
}

if (require.main === module) {
  quickTest().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = { quickTest };
