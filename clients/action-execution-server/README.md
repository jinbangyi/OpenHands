# OpenHands TypeScript Client

A comprehensive TypeScript client for the OpenHands Action Execution Server FastAPI.

## Features

- 🔄 **Full API Coverage**: Supports all OpenHands action execution endpoints
- 🛡️ **Type Safety**: Complete TypeScript type definitions for all actions and observations
- 🔄 **Retry Logic**: Built-in retry mechanism for network failures
- ⏱️ **Timeout Handling**: Configurable request timeouts
- 🔐 **Authentication**: Support for API key authentication
- 📁 **File Operations**: Upload, download, read, write, and edit files
- 🌐 **Browser Automation**: Control browser actions and interactions
- 🐍 **Python Integration**: Execute IPython/Jupyter code
- 🔧 **MCP Support**: Manage Model Context Protocol servers
- ✅ **Testing**: Comprehensive test suite with Vitest

## Installation

```bash
npm install @openhands/action-execution-client
```

## Quick Start

```typescript
import { createClient } from '@openhands/action-execution-client';

const client = createClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key', // Optional
  timeout: 30000,
  retries: 3,
});

// Check server status
const status = await client.checkAlive();
console.log('Server status:', status);

// Execute a command
const result = await client.runCommand('echo "Hello World!"');
console.log('Command output:', result.content);

// Read a file
const fileContent = await client.readFile('/path/to/file.txt');
console.log('File content:', fileContent.content);
```

## API Reference

### Client Configuration

```typescript
interface ClientConfig {
  baseUrl: string;        // OpenHands server URL
  apiKey?: string;        // Optional API key for authentication
  timeout?: number;       // Request timeout in milliseconds (default: 30000)
  retries?: number;       // Number of retry attempts (default: 3)
  retryDelay?: number;    // Delay between retries in milliseconds (default: 1000)
}
```

### Core Methods

#### Server Operations

```typescript
// Check if server is alive
await client.checkAlive();

// Get server information
await client.getServerInfo();
```

#### Command Execution

```typescript
// Run shell commands
await client.runCommand('ls -la', {
  background: false,
  timeout: 30,
  cwd: '/workspace',
  thought: 'List directory contents'
});
```

#### File Operations

```typescript
// Read file
await client.readFile('/path/to/file.txt', {
  start: 1,
  end: 100,
  viewRange: [1, 50]
});

// Write file
await client.writeFile('/path/to/file.txt', 'Hello World!', {
  start: 1,
  end: 10
});

// Edit file
await client.editFile('/path/to/file.txt', {
  oldStr: 'old text',
  newStr: 'new text',
  insertLine: 10
});

// List files
await client.listFiles('/workspace');

// Upload file
const file = new File(['content'], 'test.txt');
await client.uploadFile(file, '/destination', {
  recursive: false,
  filename: 'custom-name.txt'
});

// Download files
const blob = await client.downloadFiles('/path/to/directory');
```

#### Python/IPython Integration

```typescript
// Execute Python code
await client.runIPython(`
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
print(df.head())
`, {
  includeExtra: true,
  kernelInitCode: 'import numpy as np'
});
```

#### Browser Automation

```typescript
// Navigate to URL
await client.browseUrl('https://example.com', {
  returnAxtree: true
});

// Interactive browser actions
await client.browseInteractive(`
fill("search", "OpenHands")
click("submit-button")
wait(2000)
`, {
  returnAxtree: false
});
```

#### MCP Server Management

```typescript
// Update MCP server configuration
await client.updateMCPServer([
  {
    name: 'my-tool',
    command: 'python',
    args: ['tool.py'],
    env: { 'VAR': 'value' },
    cwd: '/workspace'
  }
]);
```

### Action Types

The client supports all OpenHands action types:

- `CmdRunAction` - Execute shell commands
- `FileReadAction` - Read file contents
- `FileWriteAction` - Write file contents
- `FileEditAction` - Edit files using OH_ACI editor
- `IPythonRunCellAction` - Execute Python code
- `BrowseURLAction` - Navigate to URLs
- `BrowseInteractiveAction` - Interactive browser actions

### Observation Types

All actions return typed observations:

- `CmdOutputObservation` - Command execution results
- `FileReadObservation` - File read results
- `FileWriteObservation` - File write results
- `FileEditObservation` - File edit results with diffs
- `IPythonRunCellObservation` - Python execution results
- `BrowseObservation` - Browser action results
- `ErrorObservation` - Error information

### Error Handling

The client includes comprehensive error handling:

```typescript
import { APIError, TimeoutError, NetworkError } from '@openhands/action-execution-client';

try {
  const result = await client.runCommand('some-command');
} catch (error) {
  if (error instanceof APIError) {
    console.error('API Error:', error.message, 'Status:', error.status);
  } else if (error instanceof TimeoutError) {
    console.error('Request timed out:', error.message);
  } else if (error instanceof NetworkError) {
    console.error('Network error:', error.message);
  }
}
```

### Configuration Management

```typescript
// Update configuration
client.updateConfig({
  timeout: 60000,
  retries: 5
});

// Set API key
client.setApiKey('new-api-key');

// Get current configuration
const config = client.getConfig();
console.log('Current config:', config);

// Cancel ongoing requests
client.cancelRequests();
```

## Examples

### Basic File Operations

```typescript
// Create, edit, and read a file
await client.writeFile('/tmp/test.txt', 'Initial content');
await client.editFile('/tmp/test.txt', {
  oldStr: 'Initial',
  newStr: 'Updated'
});
const content = await client.readFile('/tmp/test.txt');
console.log(content.content); // "Updated content"
```

### Data Analysis with Python

```typescript
const analysis = await client.runIPython(`
import pandas as pd
import matplotlib.pyplot as plt

# Load and analyze data
df = pd.read_csv('/data/sales.csv')
print(f"Dataset shape: {df.shape}")

# Create visualization
plt.figure(figsize=(10, 6))
df.groupby('month')['sales'].sum().plot(kind='bar')
plt.title('Monthly Sales')
plt.savefig('/tmp/sales_chart.png')
plt.show()
`);
```

### Web Scraping

```typescript
// Navigate and extract information
await client.browseUrl('https://news.ycombinator.com');
const data = await client.browseInteractive(`
// Extract top stories
const stories = Array.from(document.querySelectorAll('.storylink'))
  .slice(0, 5)
  .map(el => el.textContent);
console.log(JSON.stringify(stories));
`);
```

## Development

### Building

```bash
npm run build
```

### Testing

```bash
npm test
npm run test:watch
npm run test:ui
```

### Linting

```bash
npm run lint
npm run lint:fix
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- [GitHub Issues](https://github.com/All-Hands-AI/OpenHands/issues)
- [Documentation](https://docs.all-hands.dev)
- [Discord Community](https://discord.gg/ESHStjSjD4)
