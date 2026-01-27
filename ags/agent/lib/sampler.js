/**
 * Sampler Library - Unified interface for OpenAI and Claude APIs
 *
 * Supports switching between providers while maintaining a consistent interface.
 */

const { OpenAI } = require('openai');
const Anthropic = require('@anthropic-ai/sdk');

// Provider constants
const PROVIDERS = {
  OPENAI: 'openai',
  CLAUDE: 'claude'
};

// Default models for each provider
const DEFAULT_MODELS = {
  [PROVIDERS.OPENAI]: 'gpt-4o-mini',
  [PROVIDERS.CLAUDE]: 'claude-sonnet-4-20250514'
};

/**
 * Base Sampler class - defines the interface
 */
class BaseSampler {
  constructor(options = {}) {
    this.model = options.model;
    this.maxTokens = options.maxTokens || 1024;
  }

  /**
   * Send a chat completion request
   * @param {Object} params - The request parameters
   * @param {string} params.systemPrompt - The system prompt
   * @param {Array} params.messages - Array of message objects with role and content
   * @param {Object} params.options - Additional options (model, maxTokens, temperature, etc.)
   * @returns {Promise<Object>} - The response with text content
   */
  async chat(params) {
    throw new Error('chat() must be implemented by subclass');
  }

  /**
   * Stream a chat completion request
   * @param {Object} params - The request parameters
   * @returns {AsyncGenerator} - Yields text chunks
   */
  async *chatStream(params) {
    throw new Error('chatStream() must be implemented by subclass');
  }
}

/**
 * OpenAI Sampler Implementation
 */
class OpenAISampler extends BaseSampler {
  constructor(options = {}) {
    super(options);
    this.client = new OpenAI({
      apiKey: options.apiKey || process.env.OPENAI_API_KEY
    });
    this.model = options.model || DEFAULT_MODELS[PROVIDERS.OPENAI];
  }

  async chat({ systemPrompt, messages, options = {} }) {
    const model = options.model || this.model;
    const maxTokens = options.maxTokens || this.maxTokens;

    // Build messages array with system prompt
    const formattedMessages = [];

    if (systemPrompt) {
      formattedMessages.push({ role: 'system', content: systemPrompt });
    }

    // Convert messages to OpenAI format
    for (const msg of messages) {
      formattedMessages.push(this._formatMessage(msg));
    }

    const response = await this.client.chat.completions.create({
      model,
      max_tokens: maxTokens,
      temperature: options.temperature,
      messages: formattedMessages,
      ...(options.store !== undefined && { store: options.store })
    });

    return {
      text: response.choices[0].message.content,
      usage: {
        inputTokens: response.usage?.prompt_tokens,
        outputTokens: response.usage?.completion_tokens
      },
      model: response.model,
      raw: response
    };
  }

  async *chatStream({ systemPrompt, messages, options = {} }) {
    const model = options.model || this.model;
    const maxTokens = options.maxTokens || this.maxTokens;

    const formattedMessages = [];

    if (systemPrompt) {
      formattedMessages.push({ role: 'system', content: systemPrompt });
    }

    for (const msg of messages) {
      formattedMessages.push(this._formatMessage(msg));
    }

    const stream = await this.client.chat.completions.create({
      model,
      max_tokens: maxTokens,
      temperature: options.temperature,
      messages: formattedMessages,
      stream: true
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) {
        yield delta;
      }
    }
  }

  _formatMessage(msg) {
    // Handle simple text messages
    if (typeof msg.content === 'string') {
      return { role: msg.role, content: msg.content };
    }

    // Handle multimodal content (images, etc.)
    if (Array.isArray(msg.content)) {
      const content = msg.content.map(item => {
        if (item.type === 'text') {
          return { type: 'text', text: item.text };
        }
        if (item.type === 'image' || item.type === 'image_url') {
          // Support base64 or URL
          if (item.source?.data) {
            return {
              type: 'image_url',
              image_url: {
                url: `data:${item.source.media_type || 'image/jpeg'};base64,${item.source.data}`
              }
            };
          }
          if (item.image_url) {
            return { type: 'image_url', image_url: item.image_url };
          }
        }
        return item;
      });
      return { role: msg.role, content };
    }

    return { role: msg.role, content: msg.content };
  }
}

/**
 * Claude/Anthropic Sampler Implementation
 */
class ClaudeSampler extends BaseSampler {
  constructor(options = {}) {
    super(options);
    this.client = new Anthropic({
      apiKey: options.apiKey || process.env.ANTHROPIC_API_KEY
    });
    this.model = options.model || DEFAULT_MODELS[PROVIDERS.CLAUDE];
  }

  async chat({ systemPrompt, messages, options = {} }) {
    const model = options.model || this.model;
    const maxTokens = options.maxTokens || this.maxTokens;

    // Convert messages to Claude format
    const formattedMessages = messages.map(msg => this._formatMessage(msg));

    const requestParams = {
      model,
      max_tokens: maxTokens,
      messages: formattedMessages
    };

    if (systemPrompt) {
      requestParams.system = systemPrompt;
    }

    if (options.temperature !== undefined) {
      requestParams.temperature = options.temperature;
    }

    const response = await this.client.messages.create(requestParams);

    // Extract text from response
    const text = response.content
      .filter(block => block.type === 'text')
      .map(block => block.text)
      .join('');

    return {
      text,
      usage: {
        inputTokens: response.usage?.input_tokens,
        outputTokens: response.usage?.output_tokens
      },
      model: response.model,
      stopReason: response.stop_reason,
      raw: response
    };
  }

  async *chatStream({ systemPrompt, messages, options = {} }) {
    const model = options.model || this.model;
    const maxTokens = options.maxTokens || this.maxTokens;

    const formattedMessages = messages.map(msg => this._formatMessage(msg));

    const requestParams = {
      model,
      max_tokens: maxTokens,
      messages: formattedMessages,
      stream: true
    };

    if (systemPrompt) {
      requestParams.system = systemPrompt;
    }

    if (options.temperature !== undefined) {
      requestParams.temperature = options.temperature;
    }

    const stream = await this.client.messages.create(requestParams);

    for await (const event of stream) {
      if (event.type === 'content_block_delta' && event.delta?.text) {
        yield event.delta.text;
      }
    }
  }

  _formatMessage(msg) {
    // Handle simple text messages
    if (typeof msg.content === 'string') {
      return { role: msg.role, content: msg.content };
    }

    // Handle multimodal content
    if (Array.isArray(msg.content)) {
      const content = msg.content.map(item => {
        if (item.type === 'text') {
          return { type: 'text', text: item.text };
        }
        if (item.type === 'image' || item.type === 'image_url') {
          // Convert to Claude's image format
          if (item.source) {
            return {
              type: 'image',
              source: {
                type: 'base64',
                media_type: item.source.media_type || 'image/jpeg',
                data: item.source.data
              }
            };
          }
          // Convert from OpenAI format
          if (item.image_url?.url) {
            const url = item.image_url.url;
            if (url.startsWith('data:')) {
              const matches = url.match(/^data:([^;]+);base64,(.+)$/);
              if (matches) {
                return {
                  type: 'image',
                  source: {
                    type: 'base64',
                    media_type: matches[1],
                    data: matches[2]
                  }
                };
              }
            }
            // URL-based images
            return {
              type: 'image',
              source: {
                type: 'url',
                url: url
              }
            };
          }
        }
        return item;
      });
      return { role: msg.role, content };
    }

    return { role: msg.role, content: msg.content };
  }
}

/**
 * Sampler Factory - Creates the appropriate sampler based on provider
 */
class Sampler {
  /**
   * Create a new sampler instance
   * @param {Object} options - Configuration options
   * @param {string} options.provider - 'openai' or 'claude'
   * @param {string} options.apiKey - API key (optional, falls back to env vars)
   * @param {string} options.model - Model name (optional, uses defaults)
   * @param {number} options.maxTokens - Max tokens for responses (default: 1024)
   * @returns {BaseSampler} - The sampler instance
   */
  static create(options = {}) {
    const provider = options.provider || process.env.LLM_PROVIDER || PROVIDERS.OPENAI;

    switch (provider.toLowerCase()) {
      case PROVIDERS.OPENAI:
      case 'gpt':
        return new OpenAISampler(options);

      case PROVIDERS.CLAUDE:
      case 'anthropic':
        return new ClaudeSampler(options);

      default:
        throw new Error(`Unknown provider: ${provider}. Use 'openai' or 'claude'.`);
    }
  }

  /**
   * Quick chat helper - creates a sampler and sends a message
   * @param {Object} params - Chat parameters
   * @returns {Promise<Object>} - The response
   */
  static async chat(params) {
    const sampler = Sampler.create({
      provider: params.provider,
      apiKey: params.apiKey,
      model: params.model
    });
    return sampler.chat(params);
  }
}

// Export everything
module.exports = {
  Sampler,
  OpenAISampler,
  ClaudeSampler,
  PROVIDERS,
  DEFAULT_MODELS
};
