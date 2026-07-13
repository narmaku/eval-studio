export interface MetadataEntry {
  key: string;
  value: string;
}

/**
 * Convert metadata entries array to a Record, filtering out entries with empty keys.
 */
export function metadataEntriesToRecord(
  entries: MetadataEntry[],
): Record<string, string> | undefined {
  const filtered = entries.filter((e) => e.key.trim());
  if (filtered.length === 0) return undefined;
  return Object.fromEntries(filtered.map((e) => [e.key.trim(), e.value]));
}

/**
 * Convert a Record to metadata entries array.
 */
export function recordToMetadataEntries(
  record: Record<string, string> | null | undefined,
): MetadataEntry[] {
  if (!record) return [];
  return Object.entries(record).map(([key, value]) => ({ key, value }));
}

/**
 * Build auto-populated metadata from the current QA config state.
 */
export function buildAutoMetadata(config: {
  providerName?: string;
  modelName?: string;
  temperature?: number;
  topP?: number;
}): MetadataEntry[] {
  const entries: MetadataEntry[] = [];
  if (config.providerName) entries.push({ key: 'provider', value: config.providerName });
  if (config.modelName) entries.push({ key: 'model', value: config.modelName });
  if (config.temperature !== undefined)
    entries.push({ key: 'temperature', value: String(config.temperature) });
  if (config.topP !== undefined) entries.push({ key: 'top_p', value: String(config.topP) });
  return entries;
}

/**
 * Build auto-populated metadata from the current RAG endpoint config.
 */
export function buildRAGAutoMetadata(config: {
  backendType?: string;
  endpointUrl?: string;
  tableName?: string;
  embeddingModel?: string;
  generatorProviderId?: string;
}): MetadataEntry[] {
  const entries: MetadataEntry[] = [];
  if (config.backendType) entries.push({ key: 'backend_type', value: config.backendType });
  if (config.endpointUrl) entries.push({ key: 'endpoint_url', value: config.endpointUrl });
  if (config.tableName) entries.push({ key: 'table_name', value: config.tableName });
  if (config.embeddingModel) entries.push({ key: 'embedding_model', value: config.embeddingModel });
  if (config.generatorProviderId)
    entries.push({ key: 'generator_provider', value: config.generatorProviderId });
  return entries;
}

/**
 * Build auto-populated metadata from the current Arena config.
 */
export function buildArenaAutoMetadata(config: {
  contestantCount?: number;
  contestantModels?: string[];
  temperature?: number;
  topP?: number;
}): MetadataEntry[] {
  const entries: MetadataEntry[] = [];
  if (config.contestantCount !== undefined)
    entries.push({ key: 'contestant_count', value: String(config.contestantCount) });
  if (config.contestantModels && config.contestantModels.length > 0)
    entries.push({ key: 'contestant_models', value: config.contestantModels.join(', ') });
  if (config.temperature !== undefined)
    entries.push({ key: 'temperature', value: String(config.temperature) });
  if (config.topP !== undefined) entries.push({ key: 'top_p', value: String(config.topP) });
  return entries;
}
