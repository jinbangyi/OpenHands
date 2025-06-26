/**
 * OpenHands API Client Examples
 *
 * This module exports all example functions and utilities for easy import
 * and use in other projects.
 */


// Runtime sessions examples
export {
  runtimeSessionExample,
  pythonRuntimeExample,
  browserSessionExample
} from './runtime-sessions';

// Configuration and settings examples
export {
  configurationExample,
  settingsExample,
  secretsExample,
  userInfoExample,
  comprehensiveConfigCheck
} from './configuration';

// Re-export main client types for convenience
export type {
  ConversationInfo,
  ActionRequest,
  MessageAction,
  CmdRunAction,
  CreateRuntimeSessionRequest
} from '../src/index';

/**
 * Run all examples in sequence
 */
export async function runAllExamples() {
  console.log('🚀 Running all OpenHands API Client examples\n');

  const examples = [
    { name: 'Runtime Sessions', fn: () => import('./runtime-sessions').then(m => m.runtimeSessionExample()) },
    { name: 'Configuration', fn: () => import('./configuration').then(m => m.configurationExample()) },
  ];

  for (const example of examples) {
    try {
      console.log(`\n📍 Running ${example.name} example...`);
      await example.fn();
      console.log(`✅ ${example.name} completed\n`);
    } catch (error) {
      console.error(`❌ ${example.name} failed:`, error);
    }

    // Wait between examples
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  console.log('🎉 All examples completed!');
}

/**
 * Quick start function for testing the connection
 */
export async function quickStart(baseUrl: string = 'http://localhost:3000') {
  console.log('⚡ OpenHands API Client - Quick Start\n');

  try {
    const { getConfigApiOptionsConfigGet } = await import('../src/index');

    const config = await getConfigApiOptionsConfigGet({
      baseUrl,
      headers: { 'Content-Type': 'application/json' }
    });

    console.log('✅ Successfully connected to OpenHands server!');
    console.log('📋 Server config available:', !!config.data);

    return true;
  } catch (error) {
    console.error('❌ Failed to connect to OpenHands server:', error);
    console.log('\n💡 Make sure the OpenHands server is running at:', baseUrl);
    return false;
  }
}
