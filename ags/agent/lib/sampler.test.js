#!/usr/bin/env node
/**
 * Integration test for Sampler library
 *
 * Usage:
 *   OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... node sampler.test.js
 *
 * Or test individual providers:
 *   OPENAI_API_KEY=sk-... node sampler.test.js openai
 *   ANTHROPIC_API_KEY=sk-ant-... node sampler.test.js claude
 */

require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });

const { Sampler, PROVIDERS } = require('./sampler');

const TEST_PROMPT = 'Say "Hello from {provider}!" and nothing else.';

async function testChat(provider) {
  console.log(`\n--- Testing ${provider.toUpperCase()} Chat ---`);

  try {
    const sampler = Sampler.create({ provider });

    const response = await sampler.chat({
      systemPrompt: 'You are a helpful assistant. Be very brief.',
      messages: [
        { role: 'user', content: TEST_PROMPT.replace('{provider}', provider) }
      ],
      options: { maxTokens: 50 }
    });

    console.log('✓ Response:', response.text);
    console.log('✓ Model:', response.model);
    console.log('✓ Usage:', response.usage);
    return true;
  } catch (error) {
    console.error('✗ Error:', error.message);
    return false;
  }
}

async function testStream(provider) {
  console.log(`\n--- Testing ${provider.toUpperCase()} Stream ---`);

  try {
    const sampler = Sampler.create({ provider });

    process.stdout.write('✓ Streaming: ');

    const stream = sampler.chatStream({
      systemPrompt: 'You are a helpful assistant. Be very brief.',
      messages: [
        { role: 'user', content: 'Count from 1 to 5, separated by commas.' }
      ],
      options: { maxTokens: 50 }
    });

    for await (const chunk of stream) {
      process.stdout.write(chunk);
    }

    console.log('\n✓ Stream complete');
    return true;
  } catch (error) {
    console.error('✗ Error:', error.message);
    return false;
  }
}

async function testProvider(provider) {
  const chatOk = await testChat(provider);
  const streamOk = await testStream(provider);
  return chatOk && streamOk;
}

async function main() {
  console.log('=== Sampler Integration Test ===');

  const args = process.argv.slice(2);
  const results = {};

  // Determine which providers to test
  let providersToTest = [];

  if (args.length > 0) {
    // Test specific provider(s) from command line
    providersToTest = args.map(a => a.toLowerCase());
  } else {
    // Test all providers with available keys
    if (process.env.OPENAI_API_KEY) {
      providersToTest.push(PROVIDERS.OPENAI);
    }
    if (process.env.ANTHROPIC_API_KEY) {
      providersToTest.push(PROVIDERS.CLAUDE);
    }
  }

  if (providersToTest.length === 0) {
    console.error('\nNo API keys found. Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY');
    console.log('\nUsage:');
    console.log('  OPENAI_API_KEY=sk-... node sampler.test.js');
    console.log('  ANTHROPIC_API_KEY=sk-ant-... node sampler.test.js');
    console.log('  node sampler.test.js openai');
    console.log('  node sampler.test.js claude');
    process.exit(1);
  }

  // Run tests
  for (const provider of providersToTest) {
    results[provider] = await testProvider(provider);
  }

  // Summary
  console.log('\n=== Test Summary ===');
  let allPassed = true;
  for (const [provider, passed] of Object.entries(results)) {
    const status = passed ? '✓ PASS' : '✗ FAIL';
    console.log(`${status}: ${provider}`);
    if (!passed) allPassed = false;
  }

  process.exit(allPassed ? 0 : 1);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
