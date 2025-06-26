import OpenHandsClient, { createClient } from '../src';

async function main() {
  // Create client instance
  const client = createClient({
    baseUrl: 'http://localhost:33135',
    // apiKey: 'your-api-key-here', // Optional
    timeout: 30000,
    retries: 3,
  });

  try {
    // Check if server is alive
    console.log('Checking server status...');
    const status = await client.checkAlive();
    console.log('Server status:', status);

    // Get server info
    console.log('\nGetting server info...');
    const serverInfo = await client.getServerInfo();
    console.log('Server info:', serverInfo);

    // Run a simple command
    console.log('\nRunning command...');
    const cmdResult = await client.runCommand('echo "Hello from TypeScript client!"', {
      thought: 'Testing the TypeScript client',
    });
    console.log('Command result:', cmdResult);

    // Read a file (this will likely fail unless the file exists)
    console.log('\nAttempting to read a file...');
    try {
      const fileResult = await client.readFile('/etc/hostname');
      console.log('File content:', fileResult);
    } catch (error) {
      console.log('File read failed (expected):', error);
    }

    // List files in current directory
    console.log('\nListing files in root directory...');
    const files = await client.listFiles('/');
    console.log('Files:', files.slice(0, 10)); // Show first 10 files

    // Run Python code (if Jupyter is available)
    console.log('\nRunning Python code...');
    try {
      const pythonResult = await client.runIPython('print("Hello from Python!")', {
        thought: 'Testing Python execution',
      });
      console.log('Python result:', pythonResult);
    } catch (error) {
      console.log('Python execution failed (Jupyter may not be available):', error);
    }

    // Browse a URL (if browser is available)
    console.log('\nAttempting to browse a URL...');
    try {
      const browseResult = await client.browseUrl('https://httpbin.org/get', {
        thought: 'Testing browser functionality',
      });
      console.log('Browse result:', browseResult);
    } catch (error) {
      console.log('Browser operation failed (browser may not be available):', error);
    }

    console.log('\n✅ All operations completed successfully!');
  } catch (error) {
    console.error('❌ Error occurred:', error);
  }
}

// Run the example
if (require.main === module) {
  main().catch(console.error);
}

export default main;
