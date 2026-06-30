import type { components } from './generated/api';

export type Artifact = components['schemas']['ArtifactResponse'];

export interface UpdateArtifactRequest {
  description?: string;
}
