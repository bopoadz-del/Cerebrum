export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: Attachment[];
}

export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
}

export interface NavItemType {
  id: string;
  label: string;
  icon: string;
  path: string;
  category: 'main' | 'analysis' | 'tools' | 'system';
}

export interface AnalysisModule {
  id: string;
  name: string;
  description: string;
  icon: string;
  acceptedFormats: string[];
  maxFileSize: number;
}

export interface Formula {
  id: string;
  name: string;
  description: string;
  category: string;
  parameters: FormulaParameter[];
  documentationUrl?: string;
}

export interface FormulaParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array';
  required: boolean;
  description?: string;
  defaultValue?: unknown;
}

export interface AnalysisResult {
  id: string;
  moduleId: string;
  fileName: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  createdAt: Date;
  completedAt?: Date;
  summary?: string;
  details?: unknown;
  error?: string;
}

export interface DashboardStat {
  id: string;
  label: string;
  value: number;
  trend: number;
  icon: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: 'admin' | 'user' | 'auditor';
}
