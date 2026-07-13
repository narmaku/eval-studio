import { describe, it, expect } from 'vitest';
import {
  extractConfigMetadata,
  mergeMetadata,
  filterSensitiveKeys,
  formatBadgeValue,
  extractContestantSpecs,
  getSpecsDiff,
  extractSessionMetadata,
  extractJudgeMetadata,
} from './metadataUtils';
import type { EvaluationConfig } from '@/types';

// --- extractConfigMetadata ---

describe('extractConfigMetadata', () => {
  it('extracts provider name and model from config', () => {
    const config: EvaluationConfig = {
      model_endpoint: {
        provider_id: 'openai',
        name: 'OpenAI',
        default_model: 'gpt-4o',
      },
      judge_config: {},
    };
    const result = extractConfigMetadata(config);
    expect(result).toEqual(
      expect.objectContaining({
        provider: 'OpenAI',
        model: 'gpt-4o',
      }),
    );
  });

  it('extracts temperature and top_p from model_params', () => {
    const config: EvaluationConfig = {
      model_endpoint: { name: 'Test', default_model: 'test-model' },
      judge_config: {},
      model_params: { temperature: 0.7, top_p: 0.9 },
    };
    const result = extractConfigMetadata(config);
    expect(result.temperature).toBe('0.7');
    expect(result.top_p).toBe('0.9');
  });

  it('extracts max_tokens from model_params', () => {
    const config: EvaluationConfig = {
      model_endpoint: { name: 'Test', default_model: 'test-model' },
      judge_config: {},
      model_params: { max_tokens: 4096 },
    };
    const result = extractConfigMetadata(config);
    expect(result.max_tokens).toBe('4096');
  });

  it('omits undefined model_params', () => {
    const config: EvaluationConfig = {
      model_endpoint: { name: 'Test', default_model: 'test-model' },
      judge_config: {},
    };
    const result = extractConfigMetadata(config);
    expect(result).not.toHaveProperty('temperature');
    expect(result).not.toHaveProperty('top_p');
    expect(result).not.toHaveProperty('max_tokens');
  });

  it('uses provider_id as fallback when name matches default_model', () => {
    const config: EvaluationConfig = {
      model_endpoint: {
        provider_id: 'anthropic',
        name: 'claude-3-opus',
        default_model: 'claude-3-opus',
      },
      judge_config: {},
    };
    const result = extractConfigMetadata(config);
    expect(result.provider).toBe('anthropic');
  });

  it('excludes sensitive keys from model_endpoint', () => {
    const config: EvaluationConfig = {
      model_endpoint: {
        name: 'MyProvider',
        default_model: 'gpt-4o',
        api_base: 'https://secret.com/v1',
        api_key_env: 'MY_SECRET_KEY',
      },
      judge_config: {},
    };
    const result = extractConfigMetadata(config);
    expect(result).not.toHaveProperty('api_base');
    expect(result).not.toHaveProperty('api_key_env');
  });
});

// --- filterSensitiveKeys ---

describe('filterSensitiveKeys', () => {
  it('removes keys containing api_key', () => {
    const meta = { model: 'gpt-4o', api_key: 'sk-abc123' };
    expect(filterSensitiveKeys(meta)).toEqual({ model: 'gpt-4o' });
  });

  it('removes keys containing api_base', () => {
    const meta = { provider: 'openai', api_base: 'https://example.com' };
    expect(filterSensitiveKeys(meta)).toEqual({ provider: 'openai' });
  });

  it('removes api_key_env', () => {
    const meta = { model: 'gpt-4o', api_key_env: 'MY_KEY' };
    expect(filterSensitiveKeys(meta)).toEqual({ model: 'gpt-4o' });
  });

  it('removes single_model', () => {
    const meta = { model: 'gpt-4o', single_model: 'true' };
    expect(filterSensitiveKeys(meta)).toEqual({ model: 'gpt-4o' });
  });

  it('is case-insensitive', () => {
    const meta = { model: 'gpt-4o', API_KEY: 'sk-abc', API_BASE: 'https://x.com' };
    expect(filterSensitiveKeys(meta)).toEqual({ model: 'gpt-4o' });
  });

  it('returns empty object for all-sensitive input', () => {
    const meta = { api_key: 'secret', api_base: 'url' };
    expect(filterSensitiveKeys(meta)).toEqual({});
  });
});

// --- mergeMetadata ---

describe('mergeMetadata', () => {
  it('merges config and user metadata', () => {
    const config = { provider: 'openai', model: 'gpt-4o' };
    const user = { env: 'staging', notes: 'test run' };
    const result = mergeMetadata(config, user);
    expect(result).toEqual({
      provider: 'openai',
      model: 'gpt-4o',
      env: 'staging',
      notes: 'test run',
    });
  });

  it('user metadata overrides config metadata', () => {
    const config = { provider: 'openai', model: 'gpt-4o' };
    const user = { model: 'custom-model' };
    const result = mergeMetadata(config, user);
    expect(result.model).toBe('custom-model');
  });

  it('handles null user metadata', () => {
    const config = { provider: 'openai' };
    const result = mergeMetadata(config, null);
    expect(result).toEqual({ provider: 'openai' });
  });

  it('handles null config metadata', () => {
    const user = { env: 'staging' };
    const result = mergeMetadata(null, user);
    expect(result).toEqual({ env: 'staging' });
  });

  it('handles both null', () => {
    const result = mergeMetadata(null, null);
    expect(result).toEqual({});
  });
});

// --- formatBadgeValue ---

describe('formatBadgeValue', () => {
  it('returns short strings unchanged', () => {
    expect(formatBadgeValue('gpt-4o')).toBe('gpt-4o');
  });

  it('truncates strings longer than maxLength', () => {
    const long = 'this-is-a-very-long-model-name-that-should-be-truncated';
    const result = formatBadgeValue(long, 20);
    expect(result.length).toBeLessThanOrEqual(23); // 20 + '...'
    expect(result.endsWith('...')).toBe(true);
  });

  it('uses default maxLength of 24', () => {
    const long = 'abcdefghijklmnopqrstuvwxyz-extra-chars';
    const result = formatBadgeValue(long);
    expect(result.length).toBeLessThanOrEqual(27); // 24 + '...'
  });

  it('handles empty string', () => {
    expect(formatBadgeValue('')).toBe('');
  });
});

// --- extractContestantSpecs ---

describe('extractContestantSpecs', () => {
  it('extracts specs from contestants array', () => {
    const config: EvaluationConfig = {
      model_endpoint: { name: 'Test', default_model: 'test' },
      judge_config: {},
      contestants: [
        { name: 'OpenAI', default_model: 'gpt-4o', provider_id: 'openai' },
        { name: 'Anthropic', default_model: 'claude-3', provider_id: 'anthropic' },
      ],
    };
    const specs = extractContestantSpecs(config);
    expect(specs).toHaveLength(2);
    expect(specs[0].model).toBe('gpt-4o');
    expect(specs[1].model).toBe('claude-3');
  });

  it('returns empty array when no contestants', () => {
    const config: EvaluationConfig = {
      model_endpoint: { name: 'Test', default_model: 'test' },
      judge_config: {},
    };
    expect(extractContestantSpecs(config)).toEqual([]);
  });

  it('skips nested object values to avoid [object Object]', () => {
    const config: EvaluationConfig = {
      model_endpoint: { name: 'Test', default_model: 'test' },
      judge_config: {},
      contestants: [
        {
          name: 'OpenAI',
          default_model: 'gpt-4o',
          provider_id: 'openai',
          // Simulate nested object properties that could leak through
          extra_config: { nested: true },
          list_prop: [1, 2, 3],
        } as unknown as import('@/types').ModelEndpoint,
      ],
    };
    const specs = extractContestantSpecs(config);
    // Nested objects/arrays should be excluded
    expect(specs[0].fields).not.toHaveProperty('extra_config');
    expect(specs[0].fields).not.toHaveProperty('list_prop');
    // Primitives should still be included
    expect(specs[0].fields.provider).toBe('openai');
  });

  it('filters sensitive keys from contestant specs', () => {
    const config: EvaluationConfig = {
      model_endpoint: { name: 'Test', default_model: 'test' },
      judge_config: {},
      contestants: [
        {
          name: 'OpenAI',
          default_model: 'gpt-4o',
          api_base: 'https://secret.com',
          api_key_env: 'OPENAI_KEY',
        },
      ],
    };
    const specs = extractContestantSpecs(config);
    expect(specs[0].fields).not.toHaveProperty('api_base');
    expect(specs[0].fields).not.toHaveProperty('api_key_env');
  });
});

// --- getSpecsDiff ---

describe('getSpecsDiff', () => {
  it('identifies matching fields across all contestants', () => {
    const specs = [
      { model: 'gpt-4o', fields: { provider: 'openai', temperature: '0.7' } },
      { model: 'claude-3', fields: { provider: 'anthropic', temperature: '0.7' } },
    ];
    const diff = getSpecsDiff(specs);
    expect(diff.matching).toEqual({ temperature: '0.7' });
  });

  it('identifies unmatching fields', () => {
    const specs = [
      { model: 'gpt-4o', fields: { provider: 'openai', temperature: '0.7' } },
      { model: 'claude-3', fields: { provider: 'anthropic', temperature: '0.5' } },
    ];
    const diff = getSpecsDiff(specs);
    expect(diff.unmatching).toContainEqual({ key: 'provider', values: ['openai', 'anthropic'] });
    expect(diff.unmatching).toContainEqual({ key: 'temperature', values: ['0.7', '0.5'] });
  });

  it('handles fields that only exist in some contestants', () => {
    const specs = [
      { model: 'gpt-4o', fields: { provider: 'openai', max_tokens: '4096' } },
      { model: 'claude-3', fields: { provider: 'anthropic' } },
    ];
    const diff = getSpecsDiff(specs);
    // max_tokens only on one contestant, so it goes to unmatching
    expect(diff.unmatching).toContainEqual({
      key: 'max_tokens',
      values: ['4096', undefined],
    });
  });

  it('returns empty matching and unmatching for single contestant', () => {
    const specs = [{ model: 'gpt-4o', fields: { provider: 'openai' } }];
    const diff = getSpecsDiff(specs);
    // With only one contestant, all fields are "matching" (no diff to show)
    expect(diff.matching).toEqual({ provider: 'openai' });
    expect(diff.unmatching).toEqual([]);
  });

  it('returns empty for empty specs', () => {
    const diff = getSpecsDiff([]);
    expect(diff.matching).toEqual({});
    expect(diff.unmatching).toEqual([]);
  });
});

// --- extractSessionMetadata ---

describe('extractSessionMetadata', () => {
  it('extracts model, provider, harness from agent_config', () => {
    const config = {
      provider_id: 'openai',
      default_model: 'gpt-4o',
      harness_id: 'goose',
    };
    const result = extractSessionMetadata(config);
    expect(result).toEqual({
      provider: 'openai',
      model: 'gpt-4o',
      harness: 'goose',
    });
  });

  it('handles null agent_config', () => {
    expect(extractSessionMetadata(null)).toEqual({});
  });

  it('handles empty agent_config', () => {
    expect(extractSessionMetadata({})).toEqual({});
  });

  it('filters out sensitive fields', () => {
    const config = {
      provider_id: 'openai',
      default_model: 'gpt-4o',
      api_base: 'https://secret.com',
      system_prompt: 'You are a helpful assistant...',
    };
    const result = extractSessionMetadata(config);
    expect(result).not.toHaveProperty('api_base');
    expect(result).not.toHaveProperty('system_prompt');
  });

  it('extracts tool_server_ids as comma-separated tools field', () => {
    const config = {
      provider_id: 'openai',
      default_model: 'gpt-4o',
      tool_server_ids: ['filesystem', 'web-search'],
    };
    const result = extractSessionMetadata(config);
    expect(result.tools).toBe('filesystem, web-search');
  });

  it('omits tools when tool_server_ids is empty', () => {
    const config = {
      provider_id: 'openai',
      default_model: 'gpt-4o',
      tool_server_ids: [],
    };
    const result = extractSessionMetadata(config);
    expect(result).not.toHaveProperty('tools');
  });
});

// --- extractJudgeMetadata ---

describe('extractJudgeMetadata', () => {
  it('extracts judge provider and model', () => {
    const config = {
      provider_id: 'anthropic',
      model: 'claude-3-opus',
    };
    const result = extractJudgeMetadata(config);
    expect(result).toEqual({
      'judge provider': 'anthropic',
      'judge model': 'claude-3-opus',
    });
  });

  it('extracts rubric_name preferring it over rubric_id', () => {
    const config = {
      provider_id: 'openai',
      model: 'gpt-4o',
      rubric_id: 'rubric-123',
      rubric_name: 'Code Quality',
    };
    const result = extractJudgeMetadata(config);
    expect(result.rubric).toBe('Code Quality');
  });

  it('falls back to rubric_id when rubric_name is absent', () => {
    const config = {
      provider_id: 'openai',
      rubric_id: 'rubric-123',
    };
    const result = extractJudgeMetadata(config);
    expect(result.rubric).toBe('rubric-123');
  });

  it('handles null judge config', () => {
    expect(extractJudgeMetadata(null)).toEqual({});
  });

  it('handles empty judge config', () => {
    expect(extractJudgeMetadata({})).toEqual({});
  });
});
