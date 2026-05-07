export interface ParseItem {
  id: string;
  name: string;
  type: string;
  status: string;
  progress: number;
  result: string;
}

export interface CrossValidationItem {
  id: string;
  type: 'warning' | 'info' | 'error';
  message: string;
  detail: string;
}
