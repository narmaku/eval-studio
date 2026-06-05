export interface Artifact {
  id: string;
  evaluation_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  description: string | null;
  created_at: string;
}
