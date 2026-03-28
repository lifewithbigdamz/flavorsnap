export interface ClassificationResult {
  food: string;
  confidence: number;
  calories?: number;
}

export interface HistoryEntry extends ClassificationResult {
  id: number;
  timestamp: string;
}

export interface ApiErrorResponse {
  error: string;
  message?: string;
  code?: string;
}

export interface AppError {
  message: string;
  code?: string;
  details?: any;
  status?: number;
}
