// TODO: Consider generating these types from the FastAPI OpenAPI spec
// using openapi-typescript once the backend is implemented.

export type SessionMode = 'live' | 'simulated';
export type SessionStatus = 'active' | 'ended' | 'scoring' | 'completed' | 'failed';
export type MessageSender = 'user' | 'agent' | 'system' | 'judge';

export interface Session {
  id: string;
  evaluation_id: string;
  mode: SessionMode;
  status: SessionStatus;
  environment_id: string | null;
  scenario_id: string | null;
  agent_config: Record<string, unknown> | null;
  judge_config_snapshot: Record<string, unknown> | null;
  messages: Message[];
  tool_calls: ToolCall[];
  scores: SessionScore[] | null;
  error: string | null;
  started_at: string;
  ended_at: string | null;
  turn_count: number;
}

export interface Message {
  id: string;
  sender: MessageSender;
  content: string;
  timestamp: string;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: unknown;
  duration_ms: number;
  timestamp: string;
}

export interface SessionScore {
  turn_number: number | null; // null means session-level score
  dimensions: Record<string, number>;
  overall: number;
  judge_reasoning: string;
}

export interface CreateSessionRequest {
  evaluation_id: string;
  mode: SessionMode;
  agent_config?: {
    provider_id?: string;
    litellm_model?: string;
    api_base?: string;
    system_prompt?: string;
  };
  judge_config?: {
    provider_id?: string;
  };
  environment_id?: string;
  scenario_id?: string;
}

export interface SendMessageRequest {
  content: string;
}

// --- WebSocket message types ---

export type WsMessageType =
  | 'message_chunk'
  | 'message_complete'
  | 'tool_call'
  | 'score'
  | 'status'
  | 'error';

export interface WsEnvelope {
  type: WsMessageType;
  data: unknown;
  timestamp: string;
  sender: MessageSender;
  session_id: string;
}

export interface WsMessageChunk {
  type: 'message_chunk';
  data: { content: string; message_id: string };
}

export interface WsMessageComplete {
  type: 'message_complete';
  data: { content: string; message_id: string; tool_calls?: ToolCall[] };
}

export interface WsToolCallMessage {
  type: 'tool_call';
  data: ToolCall;
}

export interface WsScoreMessage {
  type: 'score';
  data: SessionScore;
}

export interface WsStatusMessage {
  type: 'status';
  data: { status: SessionStatus };
}

export interface WsErrorMessage {
  type: 'error';
  data: { message: string; code?: string };
}

export type WsMessage =
  | WsMessageChunk
  | WsMessageComplete
  | WsToolCallMessage
  | WsScoreMessage
  | WsStatusMessage
  | WsErrorMessage;
