import axios from 'axios';
import { ZipAnalysis, ChatResponse } from '../types';

// In development: empty string → requests use Vite's dev proxy (/api → localhost:5000)
// In production:  VITE_API_URL → your Render backend (e.g. https://zipfinds-api.onrender.com)
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
  persona: string = 'General',
  rawData?: any,
  location?: { lat: number; lon: number },
  history?: { role: 'user' | 'ai'; text: string }[]
): Promise<ChatResponse> => {
  const response = await apiClient.post<ChatResponse>('/api/chat', {
    zip_code: zip,
    question,
    scores,
    persona,
    raw_data: rawData,
    location,
    history,
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
