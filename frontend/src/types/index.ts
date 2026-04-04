export type ChatRole = 'user' | 'assistant' | 'system';

export type ChatMode = 'standard' | 'agent';

export type AttachmentStatus = 'uploading' | 'complete' | 'error';

export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
  status: AttachmentStatus;
  progress?: number;
}

export interface Message {
  id: string;
  role: ChatRole;
  content: string;
  attachments?: Attachment[];
  timestamp?: string;
  isThinking?: boolean;
  reasoning?: ReasoningStep[];
  metadata?: {
    webSearch?: WebSearchResult;
    codeExecution?: CodeExecutionResult;
    imageAnalysis?: string;
  };
}

export interface ReasoningStep {
  type: 'tool' | 'data' | 'thought' | 'decision';
  content: string;
  title?: string;
  details?: string;
  timestamp?: string;
  tools?: string[];
  data?: any;
}

export interface ReasoningData {
  steps: ReasoningStep[];
}

export interface CodeExecutionResult {
  output: string;
  error?: string;
  executionTime: number;
}

export interface WebSearchResult {
  query: string;
  results: {
    title: string;
    url: string;
    snippet: string;
  }[];
}

export interface ChatCompletionRequest {
  model: string;
  messages: {
    role: ChatRole;
    content: string;
  }[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: {
    index: number;
    message: {
      role: ChatRole;
      content: string;
    };
    finish_reason: string;
  }[];
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface Document {
  id: string;
  name: string;
  type: string;
  size: number;
  url: string;
  projectId?: string;
  uploadedAt: string;
  metadata?: {
    pageCount?: number;
    extractedText?: string;
    summary?: string;
  };
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  documents: Document[];
}

export interface User {
  id: string;
  email: string;
  name?: string;
  role: 'admin' | 'user';
  createdAt: string;
}

export interface Formula {
  id: string;
  name: string;
  description: string;
  category: string;
  formula: string;
  variables: {
    name: string;
    description: string;
    unit?: string;
  }[];
  parameters?: {
    name: string;
    description: string;
    unit?: string;
    default?: number;
  }[];
  example?: string;
}

export interface AnalysisResult {
  id: string;
  type: string;
  fileName?: string;
  summary?: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  result?: string;
  error?: string;
  createdAt: string;
  completedAt?: string;
  details?: any; // Flexible details for different analysis types
}

export interface CostEstimate {
  id: string;
  projectType: string;
  size: number;
  unit: string;
  location: string;
  baseCost: number;
  locationFactor: number;
  totalCost: number;
  breakdown: {
    category: string;
    cost: number;
    percentage: number;
  }[];
}
