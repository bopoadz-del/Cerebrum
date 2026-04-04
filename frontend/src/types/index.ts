export interface ReasoningStep {
  type: 'tool' | 'data' | 'thought' | 'decision';
  content: string;
  details?: string;
  timestamp?: string;
}

export interface ReasoningData {
  steps: ReasoningStep[];
  toolsConsidered?: string[];
  dataLookedUp?: string[];
  whyThisAnswer?: string;
  executionTimeMs?: number;
}

// Web Search types
export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source?: string;
  publishedDate?: string;
}

export interface WebSearchData {
  query: string;
  status: 'searching' | 'completed' | 'error';
  results?: SearchResult[];
  error?: string;
  searchTimeMs?: number;
}

// Code Execution types
export interface CodeExecutionResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  executionTimeMs: number;
  memoryUsedMb?: number;
}

export interface CodeExecutionData {
  code: string;
  language: string;
  status: 'running' | 'completed' | 'error' | 'timeout';
  result?: CodeExecutionResult;
  error?: string;
}

// Image Analysis types
export interface ImageAnalysisResult {
  description: string;
  objects?: string[];
  text?: string;
  labels?: string[];
  confidence?: number;
}

export interface ImageUpload {
  id: string;
  file: File;
  preview: string;
  status: 'uploading' | 'analyzing' | 'completed' | 'error';
  progress: number;
  result?: ImageAnalysisResult;
  error?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: Attachment[];
  reasoning?: ReasoningData;
  isThinking?: boolean;
  // New Kimi-like features
  webSearch?: WebSearchData;
  codeExecution?: CodeExecutionData;
  imageAnalysis?: ImageAnalysisResult;
  suggestedReplies?: string[];
}

export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
  status?: 'uploading' | 'processing' | 'complete' | 'error';
  uploadProgress?: number;
  error?: string;
  metadata?: