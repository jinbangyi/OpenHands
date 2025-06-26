/**
 * Simple JavaScript example using the OpenHands TypeScript client
 * This can be run directly with Node.js after building the TypeScript client
 */

const { createClient } = require('@openhands/action-execution-client');

async function simpleExample() {
  // Create client
  const client = createClient({
    baseUrl: 'http://localhost:33135',
    apiKey: process.env.OPENHANDS_API_KEY, // Optional
  });

  try {
    console.log('🚀 Starting OpenHands client test...\n');

    // 1. Check server status
    console.log('📡 Checking server status...');
    const status = await client.checkAlive();
    console.log('✅ Server status:', status.status);

    // 2. Get server info
    console.log('\n📊 Getting server information...');
    const serverInfo = await client.getServerInfo();
    console.log('📈 Uptime:', Math.round(serverInfo.uptime), 'seconds');
    console.log('💾 Memory usage:', Math.round(serverInfo.resources.memory_percent), '%');
    console.log('🖥️  CPU usage:', Math.round(serverInfo.resources.cpu_percent), '%');

    // 3. Run a simple command
    console.log('\n💻 Running shell command...');
    const cmdResult = await client.runCommand('whoami && date && pwd');
    console.log('📝 Command output:');
    console.log(cmdResult.content);

    // 4. Create and read a test file
    console.log('\n📄 Creating test file...');
    await client.writeFile('/tmp/client-test.txt', 'Hello from JavaScript client!\nTimestamp: ' + new Date().toISOString());

    const fileContent = await client.readFile('/tmp/client-test.txt');
    console.log('📖 File content:');
    console.log(fileContent.content);

    // 5. List files in /tmp
    console.log('\n📁 Listing files in /tmp...');
    const files = await client.listFiles('/tmp');
    console.log('📋 Files found:', files.filter(f => f.includes('client-test')));

    // 6. Clean up
    console.log('\n🧹 Cleaning up...');
    await client.runCommand('rm -f /tmp/client-test.txt');

    console.log('\n✅ All tests completed successfully!');

  } catch (error) {
    console.error('❌ Error occurred:', error.message);
    if (error.status) {
      console.error('📊 HTTP Status:', error.status);
    }
  }
}

// Run if called directly
if (require.main === module) {
  simpleExample().catch(console.error);
}

module.exports = { simpleExample };
