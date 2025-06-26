import OpenHandsClient, { createClient } from '../src';

const localPort = process.env.OPENHANDS_PORT || '33135';

// Example demonstrating advanced file operations
async function fileOperationsExample() {
  const client = createClient({
    baseUrl: `http://localhost:${localPort}`,
    apiKey: process.env.OPENHANDS_API_KEY,
  });

  try {
    console.log('=== File Operations Example ===\n');

    // Create a test file
    console.log('Creating test file...');
    const writeResult = await client.writeFile(
      '/tmp/test-file.txt',
      'Hello World!\nThis is a test file created by the TypeScript client.\nLine 3\nLine 4',
      { thought: 'Creating a test file for demonstration' }
    );
    console.log('Write result:', writeResult);

    // Read the entire file
    console.log('\nReading entire file...');
    const readResult = await client.readFile('/tmp/test-file.txt');
    console.log('Read result:', readResult);

    // Read partial file (lines 2-3)
    console.log('\nReading partial file (lines 2-3)...');
    const partialReadResult = await client.readFile('/tmp/test-file.txt', {
      start: 2,
      end: 3,
    });
    console.log('Partial read result:', partialReadResult);

    // Edit the file using string replacement
    console.log('\nEditing file using string replacement...');
    const editResult = await client.editFile('/tmp/test-file.txt', {
      oldStr: 'Hello World!',
      newStr: 'Hello OpenHands!',
      thought: 'Replacing greeting text',
    });
    console.log('Edit result:', editResult);

    // Read the file again to see changes
    console.log('\nReading file after edit...');
    const readAfterEdit = await client.readFile('/tmp/test-file.txt');
    console.log('File after edit:', readAfterEdit);

    // Clean up
    console.log('\nCleaning up...');
    const cleanupResult = await client.runCommand('rm /tmp/test-file.txt');
    console.log('Cleanup result:', cleanupResult);

  } catch (error) {
    console.error('Error in file operations:', error);
  }
}

// Example demonstrating browser automation
async function browserAutomationExample() {
  const client = createClient({
    baseUrl: `http://localhost:${localPort}`,
    apiKey: process.env.OPENHANDS_API_KEY,
  });

  try {
    console.log('\n=== Browser Automation Example ===\n');

    // Navigate to a test page
    console.log('Navigating to test page...');
    const browseResult = await client.browseUrl('https://httpbin.org/forms/post', {
      returnAxtree: true,
      thought: 'Loading form page for testing',
    });

    delete browseResult.extras.screenshot;
    delete browseResult.extras.set_of_marks;
    console.log('Browse result:', browseResult);

    // Perform interactive actions
    console.log('\nFilling out form...');
    const interactiveResult = await client.browseInteractive(
      `
      fill("custname", "John Doe")
      fill("custtel", "123-456-7890")
      fill("custemail", "john@example.com")
      select("size", "medium")
      click("submit")
      `,
      {
        returnAxtree: true,
        thought: 'Filling out and submitting the form',
      }
    );
    console.log('Interactive result:', interactiveResult);

  } catch (error) {
    console.error('Error in browser automation:', error);
  }
}

// Example demonstrating Python/Jupyter integration
async function pythonIntegrationExample() {
  const client = createClient({
    baseUrl: `http://localhost:${localPort}`,
    apiKey: process.env.OPENHANDS_API_KEY,
  });

  try {
    console.log('\n=== Python Integration Example ===\n');

    // Run basic Python code
    console.log('Running basic Python code...');
    const basicPython = await client.runIPython(`
import sys
import os
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
    `, {
      thought: 'Getting Python environment info',
      includeExtra: true,
    });
    console.log('Basic Python result:', basicPython);

    // Run data analysis code
    console.log('\nRunning data analysis...');
    const dataAnalysisCode = `
import pandas as pd
import numpy as np

# Create sample data
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'Diana'],
    'age': [25, 30, 35, 28],
    'salary': [50000, 60000, 70000, 55000]
}

df = pd.DataFrame(data)
print("Sample DataFrame:")
print(df)
print("\\nAverage age:", df['age'].mean())
print("Average salary: $" + f"{df['salary'].mean():,.2f}")
    `;

    const dataAnalysis = await client.runIPython(dataAnalysisCode, {
      thought: 'Performing data analysis with pandas',
    });
    console.log('Data analysis result:', dataAnalysis);

    // Create a simple plot
    console.log('\nCreating a plot...');
    const plotResult = await client.runIPython(`
import matplotlib.pyplot as plt

plt.figure(figsize=(8, 6))
plt.bar(df['name'], df['salary'])
plt.title('Salary by Person')
plt.xlabel('Name')
plt.ylabel('Salary ($)')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('/tmp/salary_plot.png', dpi=150, bbox_inches='tight')
plt.show()

print("Plot saved to /tmp/salary_plot.png")
    `, {
      thought: 'Creating a salary visualization',
    });
    console.log('Plot result:', plotResult);

  } catch (error) {
    console.error('Error in Python integration:', error);
  }
}

// Main function to run all examples
async function runExamples() {
  await fileOperationsExample();
  await browserAutomationExample();
  await pythonIntegrationExample();
}

export {
  fileOperationsExample,
  browserAutomationExample,
  pythonIntegrationExample,
  runExamples,
};

// Run the example
if (require.main === module) {
  runExamples().catch(console.error);
}

export default runExamples;
