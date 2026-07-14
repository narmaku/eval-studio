import type { EvaluationConfig, ModelEndpoint } from '@/types';

/** Keys to exclude from display — sensitive or cosmetically useless. */
const SENSITIVE_KEY_PATTERNS = [
  'api_key',
  'api_base',
  'api_key_env',
  'single_model',
  'system_prompt',
  'endpoint_url',
  'ssl_cert',
  'ssl_client',
  'proxy',
  'secret',
  'token',
  'password',
  'credential',
];

/**
 * Check if a key matches any sensitive pattern (case-insensitive).
 */
function isSensitiveKey(key: string): boolean {
  const lower = key.toLowerCase();
  return SENSITIVE_KEY_PATTERNS.some((pattern) => lower.includes(pattern));
}

/**
 * Remove sensitive keys from a metadata record.
 */
export function filterSensitiveKeys(metadata: Record<string, string>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(metadata)) {
    if (!isSensitiveKey(key)) {
      result[key] = value;
    }
  }
  return result;
}

/**
 * Extract display-friendly metadata from an EvaluationConfig.
 * Pulls provider name, model, and any defined model_params (temperature, top_p, etc.).
 */
export function extractConfigMetadata(config: EvaluationConfig): Record<string, string> {
  const meta: Record<string, string> = {};
  const ep = config.model_endpoint;

  if (!ep) return meta;

  // Provider: use name unless it duplicates the model, then fall back to provider_id
  if (ep.name && ep.name !== ep.default_model) {
    meta.provider = ep.name;
  } else if (ep.provider_id) {
    meta.provider = ep.provider_id;
  }

  // Model
  if (ep.default_model) {
    meta.model = ep.default_model;
  }

  // Model params
  const params = config.model_params;
  if (params) {
    if (params.temperature !== undefined) {
      meta.temperature = String(params.temperature);
    }
    if (params.top_p !== undefined) {
      meta.top_p = String(params.top_p);
    }
    if (params.max_tokens !== undefined) {
      meta.max_tokens = String(params.max_tokens);
    }
    if (params.frequency_penalty !== undefined) {
      meta.frequency_penalty = String(params.frequency_penalty);
    }
    if (params.presence_penalty !== undefined) {
      meta.presence_penalty = String(params.presence_penalty);
    }
  }

  return meta;
}

/**
 * Merge config-extracted metadata with user-supplied metadata.
 * User metadata takes precedence over config-extracted metadata.
 */
export function mergeMetadata(
  configMeta: Record<string, string> | null | undefined,
  userMeta: Record<string, string> | null | undefined,
): Record<string, string> {
  return {
    ...(configMeta ?? {}),
    ...(userMeta ?? {}),
  };
}

/**
 * Truncate long badge values for display.
 */
export function formatBadgeValue(value: string, maxLength: number = 24): string {
  if (value.length <= maxLength) return value;
  return value.slice(0, maxLength) + '...';
}

/** Spec entry for a single contestant. */
export interface ContestantSpec {
  model: string;
  fields: Record<string, string>;
}

/**
 * Extract per-contestant specs from an arena evaluation config.
 * Strips sensitive keys from each contestant's fields.
 */
export function extractContestantSpecs(config: EvaluationConfig): ContestantSpec[] {
  if (!config.contestants || config.contestants.length === 0) return [];

  return config.contestants.map((contestant: ModelEndpoint) => {
    const fields: Record<string, string> = {};

    if (contestant.provider_id) fields.provider = contestant.provider_id;
    if (contestant.name && contestant.name !== contestant.default_model) {
      fields.name = contestant.name;
    }
    if (contestant.tags && contestant.tags.length > 0) {
      fields.tags = contestant.tags.join(', ');
    }

    // Add any extra keys from the contestant object that aren't already covered
    // (ModelEndpoint might have additional properties beyond the typed interface)
    const raw = contestant as unknown as Record<string, unknown>;
    for (const [key, val] of Object.entries(raw)) {
      if (
        val !== undefined &&
        val !== null &&
        !['name', 'default_model', 'provider_id', 'tags'].includes(key)
      ) {
        // Skip non-primitive values (objects/arrays) to avoid "[object Object]" in badges
        if (typeof val === 'object') continue;
        fields[key] = String(val);
      }
    }

    return {
      model: contestant.default_model,
      fields: filterSensitiveKeys(fields),
    };
  });
}

/** Result of comparing specs across contestants. */
export interface SpecsDiff {
  /** Fields that have the same value across all contestants. */
  matching: Record<string, string>;
  /** Fields that differ — one entry per key with values array (one per contestant). */
  unmatching: { key: string; values: (string | undefined)[] }[];
}

/**
 * Compare specs across contestants and categorize into matching/unmatching fields.
 */
export function getSpecsDiff(specs: ContestantSpec[]): SpecsDiff {
  if (specs.length === 0) return { matching: {}, unmatching: [] };

  // Collect all unique keys across all contestants
  const allKeys = new Set<string>();
  for (const spec of specs) {
    for (const key of Object.keys(spec.fields)) {
      allKeys.add(key);
    }
  }

  const matching: Record<string, string> = {};
  const unmatching: { key: string; values: (string | undefined)[] }[] = [];

  for (const key of allKeys) {
    const values = specs.map((s) => s.fields[key]);

    // Check if all values are the same (and all defined)
    const allSame = values.every((v) => v !== undefined && v === values[0]);

    if (allSame) {
      matching[key] = values[0]!;
    } else {
      unmatching.push({ key, values });
    }
  }

  return { matching, unmatching };
}

/**
 * Extract metadata from a session's agent_config for display as badges.
 */
export function extractSessionMetadata(
  agentConfig: Record<string, unknown> | null | undefined,
): Record<string, string> {
  if (!agentConfig) return {};

  const meta: Record<string, string> = {};

  // Well-known fields
  if (agentConfig.provider_id) meta.provider = String(agentConfig.provider_id);
  if (agentConfig.default_model) meta.model = String(agentConfig.default_model);
  if (agentConfig.harness_id) meta.harness = String(agentConfig.harness_id);
  if (agentConfig.evaluator_id) meta.evaluator = String(agentConfig.evaluator_id);

  // Tool servers (array of IDs)
  const toolServers = agentConfig.tool_server_ids;
  if (Array.isArray(toolServers) && toolServers.length > 0) {
    meta.tools = toolServers.map(String).join(', ');
  }

  return meta;
}

/**
 * Extract metadata from a session's judge_config_snapshot for display as badges.
 */
export function extractJudgeMetadata(
  judgeConfig: Record<string, unknown> | null | undefined,
): Record<string, string> {
  if (!judgeConfig) return {};

  const meta: Record<string, string> = {};

  if (judgeConfig.provider_id) meta['judge provider'] = String(judgeConfig.provider_id);
  if (judgeConfig.model) meta['judge model'] = String(judgeConfig.model);
  if (judgeConfig.rubric_id) meta.rubric = String(judgeConfig.rubric_id);
  if (judgeConfig.rubric_name) meta.rubric = String(judgeConfig.rubric_name);

  return meta;
}
