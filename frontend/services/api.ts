import axios from 'axios';
import { ZipAnalysis, ChatResponse } from '../types';

// Use relative URLs so requests go through Vite's dev proxy.
// The proxy (vite.config.ts) forwards /api/* to the Flask backend.
// For production, set VITE_API_URL to your deployed backend URL.
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30s — some API calls can be slow first time
});

export const analyzeZip = async (zip: string): Promise<ZipAnalysis> => {
  const response = await apiClient.get<ZipAnalysis>(`/api/analyze/${zip}`);
  return response.data;
};

export const compareZips = async (zips: string[]): Promise<ZipAnalysis[]> => {
  const zipQuery = zips.join(',');
  const response = await apiClient.get<ZipAnalysis[]>(`/api/compare?zips=${zipQuery}`);
  return response.data;
};

export const chatWithZip = async (
  zip: string,
  question: string,
  scores: any,
  persona: string = 'General'
): Promise<ChatResponse> => {
  const response = await apiClient.post<ChatResponse>('/api/chat', {
    zip_code: zip,
    question,
    scores,
    persona,
  });
  return response.data;
};

export const fetchNarrative = async (
  zip: string,
  scores: any,
  persona: string = 'General'
): Promise<{ narrative: string }> => {
  const response = await apiClient.post<{ narrative: string }>('/api/narrative', {
    zip_code: zip,
    scores,
    persona,
  });
  return response.data;
};

export const fetchPersonas = async (): Promise<string[]> => {
  const response = await apiClient.get<{ personas: string[] }>('/api/personas');
  return response.data.personas;
};
