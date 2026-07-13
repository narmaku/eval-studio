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
 * Build auto-populated metadata from the current config state.
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
