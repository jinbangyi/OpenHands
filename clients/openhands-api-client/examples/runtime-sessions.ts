/**
 * Runtime Sessions Example for OpenHands API Client
 *
 * This example demonstrates how to create and manage runtime sessions,
 * execute commands, and manage browser interactions.
 */

import {
  listRuntimeSessionsApiRuntimeSessionsGet,
  createRuntimeSessionApiRuntimeSessionsPost,
  getRuntimeSessionInfoApiRuntimeSessionsSessionIdGet,
  executeCommandApiRuntimeSessionsSessionIdExecutePost,
  getRuntimeSessionConfigApiRuntimeSessionsSessionIdConfigGet,
  getRuntimeSessionEventsApiRuntimeSessionsSessionIdEventsGet,
  addRuntimeSessionEventApiRuntimeSessionsSessionIdEventsPost,
  closeRuntimeSessionApiRuntimeSessionsSessionIdDelete,
  getWebHostsApiRuntimeSessionsSessionIdWebHostsGet,
  getRuntimeSessionScreenshotApiRuntimeBrowserSessionIdScreenshotGet,
  getBrowserStatusApiRuntimeBrowserSessionIdBrowserStatusGet,
  type CreateRuntimeSessionRequest,
  type ActionRequest,
  type CmdRunAction,
  type IPythonRunCellAction,
  type FileWriteAction,
  type BrowseUrlAction,
} from '../src/index';

// Configuration
const BASE_URL = 'http://localhost:3000';
const API_CONFIG = {
  baseUrl: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
};

async function runtimeSessionExample() {
  console.log('🖥️  OpenHands API Client - Runtime Sessions Example\n');

  try {
    // 1. List existing runtime sessions
    console.log('📋 Listing existing runtime sessions...');
    const existingSessions = await listRuntimeSessionsApiRuntimeSessionsGet(API_CONFIG);
    console.log('Existing sessions:', existingSessions.data);

    // 2. Create a new runtime session
    console.log('\n🆕 Creating new runtime session...');
    const sessionRequest: CreateRuntimeSessionRequest = {
      session_id: null, // Let the server generate one
    };

    const sessionResponse = await createRuntimeSessionApiRuntimeSessionsPost({
      ...API_CONFIG,
      body: sessionRequest
    });

    const sessionId = sessionResponse.data?.session_id;
    if (!sessionId) {
      throw new Error('Failed to create session');
    }

    console.log(`Created session: ${sessionId}`);

    // 3. Get session information
    console.log('\n📊 Getting session information...');
    const sessionInfo = await getRuntimeSessionInfoApiRuntimeSessionsSessionIdGet({
      ...API_CONFIG,
      path: { session_id: sessionId }
    });
    console.log('Session info:', sessionInfo.data);

    // 4. Get session configuration
    console.log('\n⚙️  Getting session configuration...');
    const sessionConfig = await getRuntimeSessionConfigApiRuntimeSessionsSessionIdConfigGet({
      ...API_CONFIG,
      path: { session_id: sessionId }
    });
    console.log('Session config:', sessionConfig.data);

    // 5. Execute a command in the session
    console.log('\n🔧 Executing command in session...');
    const commandAction: ActionRequest = {
      action: 'run',
      args: {
        command: 'echo "Hello from OpenHands runtime session!"',
        blocking: true
      } as CmdRunAction
    };

    const commandResult = await executeCommandApiRuntimeSessionsSessionIdExecutePost({
      ...API_CONFIG,
      path: { session_id: sessionId },
      body: commandAction
    });
    console.log('Command result:', commandResult.data);

    // 6. Execute a file system command
    console.log('\n📁 Listing files in session...');
    const lsAction: ActionRequest = {
      action: 'run',
      args: {
        command: 'ls -la',
        blocking: true
      } as CmdRunAction
    };

    const lsResult = await executeCommandApiRuntimeSessionsSessionIdExecutePost({
      ...API_CONFIG,
      path: { session_id: sessionId },
      body: lsAction
    });
    console.log('Directory listing:', lsResult.data);

    // wait for a moment to ensure the session is ready
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 7. Get session events
    console.log('\n📥 Getting session events...');
    const events = await getRuntimeSessionEventsApiRuntimeSessionsSessionIdEventsGet({
      ...API_CONFIG,
      path: { session_id: sessionId },
      query: {
        limit: 10,
        reverse: true // Get the most recent events
      }
    });
    console.log('Session events:', events.data);

    // 8. Get web hosts (if available)
    console.log('\n🌐 Getting web hosts...');
    try {
      const webHosts = await getWebHostsApiRuntimeSessionsSessionIdWebHostsGet({
        ...API_CONFIG,
        path: { session_id: sessionId }
      });
      console.log('Web hosts:', webHosts.data);
    } catch (error) {
      console.log('No web hosts available');
    }

    // 9. Close the session
    console.log('\n🔒 Closing session...');
    await closeRuntimeSessionApiRuntimeSessionsSessionIdDelete({
      ...API_CONFIG,
      path: { session_id: sessionId }
    });
    console.log('Session closed successfully!');

    console.log('\n✅ Runtime session example completed!');

  } catch (error) {
    console.error('❌ Error in runtime session example:', error);
  }
}

// Advanced runtime session with Python execution
async function pythonRuntimeExample() {
  console.log('🐍 OpenHands API Client - Python Runtime Example\n');

  try {
    // Create a Python-focused runtime session
    const sessionResponse = await createRuntimeSessionApiRuntimeSessionsPost({
      ...API_CONFIG,
      body: {
        session_id: null
      }
    });

    const sessionId = sessionResponse.data?.session_id;
    if (!sessionId) {
      throw new Error('Failed to create Python session');
    }

    console.log(`Created Python session: ${sessionId}`);

    // Install some Python packages
    console.log('\n📦 Installing Python packages...');
    const installAction: ActionRequest = {
      action: 'run',
      args: {
        command: 'pip install requests numpy pandas',
        blocking: true
      } as CmdRunAction
    };

    await executeCommandApiRuntimeSessionsSessionIdExecutePost({
      ...API_CONFIG,
      path: { session_id: sessionId },
      body: installAction
    });

    // Execute Python code
    console.log('\n🐍 Executing Python code...');
    const pythonAction: ActionRequest = {
      action: 'run_ipython',
      args: {
        code: `
import numpy as np
import pandas as pd

# Create some sample data
data = np.random.randn(10, 3)
df = pd.DataFrame(data, columns=['A', 'B', 'C'])
print("Sample DataFrame:")
print(df.head())
print(f"Shape: {df.shape}")
        `.trim()
      } as IPythonRunCellAction
    };

    const pythonResult = await executeCommandApiRuntimeSessionsSessionIdExecutePost({
      ...API_CONFIG,
      path: { session_id: sessionId },
      body: pythonAction
    });
    console.log('Python execution result:', pythonResult.data);

    // Create a simple Python file
    console.log('\n📄 Creating Python file...');
    const createFileAction: ActionRequest = {
      action: 'write',
      args: {
        path: '/tmp/hello.py',
        content: `
def greet(name):
    return f"Hello, {name}! Welcome to OpenHands."

if __name__ == "__main__":
    print(greet("Developer"))
    print("This file was created via OpenHands API!")
        `.trim()
      } as FileWriteAction
    };

    await executeCommandApiRuntimeSessionsSessionIdExecutePost({
      ...API_CONFIG,
      path: { session_id: sessionId },
      body: createFileAction
    });

    // Run the Python file
    console.log('\n▶️  Running Python file...');
    const runFileAction: ActionRequest = {
      action: 'run',
      args: {
        command: 'python /tmp/hello.py',
        blocking: true
      } as CmdRunAction
    };

    const runResult = await executeCommandApiRuntimeSessionsSessionIdExecutePost({
      ...API_CONFIG,
      path: { session_id: sessionId },
      body: runFileAction
    });
    console.log('Python file execution:', runResult.data);

    // Get session events
    console.log('\n📥 Getting session events...');
    const events = await getRuntimeSessionEventsApiRuntimeSessionsSessionIdEventsGet({
      ...API_CONFIG,
      path: { session_id: sessionId },
      query: {
        limit: 10,
        reverse: true // Get the most recent events
      }
    });
    console.log('Session events:', events.data);

    // Clean up
    await closeRuntimeSessionApiRuntimeSessionsSessionIdDelete({
      ...API_CONFIG,
      path: { session_id: sessionId }
    });

    console.log('\n✅ Python runtime example completed!');

  } catch (error) {
    console.error('❌ Error in Python runtime example:', error);
  }
}

// Browser session example
async function browserSessionExample() {
  console.log('🌐 OpenHands API Client - Browser Session Example\n');

  try {
    // Create a browser-enabled session
    const sessionResponse = await createRuntimeSessionApiRuntimeSessionsPost({
      ...API_CONFIG,
      body: {
        session_id: null
      }
    });

    const sessionId = sessionResponse.data?.session_id;
    if (!sessionId) {
      throw new Error('Failed to create browser session');
    }

    console.log(`Created browser session: ${sessionId}`);

    // Check browser status
    console.log('\n🔍 Checking browser status...');
    try {
      const browserStatus = await getBrowserStatusApiRuntimeBrowserSessionIdBrowserStatusGet({
        ...API_CONFIG,
        path: { session_id: sessionId }
      });
      console.log('Browser status:', browserStatus.data);
    } catch (error) {
      console.log('Browser not available in this session');
    }

    // Take a screenshot (if browser is available)
    console.log('\n📸 Taking screenshot...');
    try {
      const screenshot = await getRuntimeSessionScreenshotApiRuntimeBrowserSessionIdScreenshotGet({
        ...API_CONFIG,
        path: { session_id: sessionId }
      });
      console.log('Screenshot taken:', !!screenshot.data);
    } catch (error) {
      console.log('Screenshot not available');
    }

    // Execute a browse action
    console.log('\n🌐 Executing browse action...');
    const browseAction: ActionRequest = {
      action: 'browse',
      args: {
        url: 'https://httpbin.org/json'
      } as BrowseUrlAction
    };

    try {
      const browseResult = await executeCommandApiRuntimeSessionsSessionIdExecutePost({
        ...API_CONFIG,
        path: { session_id: sessionId },
        body: browseAction
      });
      console.log('Browse result:', browseResult.data);
    } catch (error) {
      console.log('Browse action not available');
    }

    // Clean up
    await closeRuntimeSessionApiRuntimeSessionsSessionIdDelete({
      ...API_CONFIG,
      path: { session_id: sessionId }
    });

    console.log('\n✅ Browser session example completed!');

  } catch (error) {
    console.error('❌ Error in browser session example:', error);
  }
}

export {
  runtimeSessionExample,
  pythonRuntimeExample,
  browserSessionExample
};

// Run example if called directly
if (typeof window === 'undefined') {
  const examples = {
    '1': runtimeSessionExample,
    '2': pythonRuntimeExample,
    '3': browserSessionExample
  };

  const choice = '3'; // Default choice
  const exampleFunc = examples[choice as keyof typeof examples] || runtimeSessionExample;

  exampleFunc().catch(console.error);
}
