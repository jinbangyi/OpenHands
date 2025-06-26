# OpenHands API Client

A TypeScript client library for the OpenHands API, providing type-safe access to all OpenHands endpoints.

## Installation

```bash
npm install @openhands/api-client
```

## Basic Usage

```typescript
import { OpenHandsAPIClient } from '@openhands/api-client';

// Initialize the client
const client = new OpenHandsAPIClient({
  baseUrl: 'http://localhost:3000',
  apiKey: 'your-api-key', // Optional
  timeout: 30000, // Optional: 30 seconds default
  retries: 3, // Optional: 3 retries default
});

// Create a new conversation
const conversation = await client.createConversation({
  repository: 'owner/repo',
  git_provider: 'github',
  initial_user_msg: 'Hello, OpenHands!',
});

// Start the conversation
await client.startConversation(conversation.conversation_id);

// List files in the workspace
const files = await client.listFiles(conversation.conversation_id);

// Get conversation events
const events = await client.searchEvents(conversation.conversation_id, {
  limit: 10,
  reverse: true,
});
```

## API Coverage

This client provides comprehensive coverage of the OpenHands API including:

### Options API
- `getModels()` - Get supported LLM models
- `getAgents()` - Get available agents
- `getSecurityAnalyzers()` - Get security analyzers
- `getConfig()` - Get current configuration

### Conversations API
- `createConversation(request)` - Create new conversation
- `searchConversations(params)` - Search conversations with pagination
- `getConversation(id)` - Get conversation details
- `deleteConversation(id)` - Delete conversation
- `startConversation(id)` - Start agent loop
- `stopConversation(id)` - Stop agent loop
- `listFiles(id, path)` - List workspace files
- `selectFile(id, file)` - Get file content
- `zipWorkspace(id)` - Download workspace as zip
- `getGitChanges(id)` - Get git changes
- `getGitDiff(id, path)` - Get git diff
- `submitFeedback(id, feedback)` - Submit user feedback
- `searchEvents(id, params, filter)` - Search event stream
- `addEvent(id, event)` - Add event
- `getMicroagents(id)` - Get microagents
- `getTrajectory(id)` - Get trajectory

### Runtime Sessions API
- `listRuntimeSessions()` - List runtime sessions
- `createRuntimeSession(request)` - Create runtime session
- `getRuntimeSession(id)` - Get session info
- `closeRuntimeSession(id)` - Close session
- `executeCommand(id, command)` - Execute command
- `getRuntimeSessionEvents(id, params, filter)` - Get session events
- `addRuntimeSessionEvent(id, event)` - Add session event

### Browser API
- `getRuntimeSessionScreenshot(id)` - Get browser screenshot
- `getBrowserStatus(id)` - Get browser status

### Settings API
- `getSettings()` - Load user settings
- `saveSettings(settings)` - Store user settings
- `saveProviderTokens(tokens)` - Store provider tokens
- `unsetProviderTokens()` - Unset provider tokens

### Secrets API
- `getCustomSecrets()` - Load custom secrets
- `createCustomSecret(secret)` - Create custom secret
- `updateCustomSecret(id, secret)` - Update custom secret
- `deleteCustomSecret(id)` - Delete custom secret

### User API
- `getUserRepositories(sort)` - Get user repositories
- `getUser()` - Get user information
- `searchRepositories(params)` - Search repositories
- `getSuggestedTasks()` - Get suggested tasks
- `getRepositoryBranches(repo)` - Get repository branches

### Health API
- `alive()` - Check if server is alive
- `health()` - Get health status
- `getServerInfo()` - Get server information

## Error Handling

The client provides structured error handling with custom error types:

```typescript
import { APIError, NetworkError, TimeoutError } from '@openhands/api-client';

try {
  await client.getUser();
} catch (error) {
  if (error instanceof APIError) {
    console.error(`API Error ${error.status}: ${error.message}`);
    console.error('Response:', error.response);
  } else if (error instanceof NetworkError) {
    console.error('Network Error:', error.message);
  } else if (error instanceof TimeoutError) {
    console.error('Request timed out:', error.message);
  }
}
```

## Configuration

### Client Configuration

```typescript
interface ClientConfig {
  baseUrl: string;           // Required: API base URL
  apiKey?: string;          // Optional: Authentication token
  timeout?: number;         // Optional: Request timeout in ms (default: 30000)
  retries?: number;         // Optional: Number of retries (default: 3)
  retryDelay?: number;      // Optional: Delay between retries in ms (default: 1000)
}
```

### Request Options

You can override default options for individual requests:

```typescript
await client.getModels({
  timeout: 60000,  // 60 seconds for this request
  retries: 5,      // 5 retries for this request
  headers: {       // Additional headers
    'Custom-Header': 'value'
  }
});
```

## WebSocket Support

For real-time communication, you'll need to establish a WebSocket connection separately. The conversation ID from `createConversation()` can be used to connect to the WebSocket endpoint.

## TypeScript Support

This library is written in TypeScript and provides comprehensive type definitions for all API requests and responses. All types are exported and can be imported for use in your application:

```typescript
import {
  ConversationInfo,
  ConversationResponse,
  Repository,
  User,
  Settings,
  // ... and many more
} from '@openhands/api-client';
```

## Development

```bash
# Install dependencies
npm install

# Build the library
npm run build

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint
```

## License

MIT
