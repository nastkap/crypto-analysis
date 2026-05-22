import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// System endpoints
export const getSystemStatus = async () => {
  try {
    const response = await apiClient.get('/status');
    return response.data;
  } catch (error) {
    console.error('Error fetching system status:', error);
    throw error;
  }
};

export const getK8sPods = async () => {
  try {
    const response = await apiClient.get('/k8s/pods');
    return response.data;
  } catch (error) {
    console.error('Error fetching K8s pods:', error);
    throw error;
  }
};

// Benchmark endpoints
export const runBenchmark = async (config) => {
  try {
    const response = await apiClient.post('/benchmark/run', config);
    return response.data;
  } catch (error) {
    console.error('Error running benchmark:', error);
    throw error;
  }
};

export const getBenchmarkStatus = async (benchmarkId) => {
  try {
    const response = await apiClient.get(`/benchmark/${benchmarkId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching benchmark status:', error);
    throw error;
  }
};

export const getBenchmarkResults = async () => {
  try {
    const response = await apiClient.get('/results');
    return response.data;
  } catch (error) {
    console.error('Error fetching benchmark results:', error);
    throw error;
  }
};

export const getBenchmarkResultsCSV = async () => {
  try {
    const response = await apiClient.get('/results/download?format=csv', {
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    console.error('Error downloading CSV:', error);
    throw error;
  }
};

// Health check
export const healthCheck = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('Error checking health:', error);
    return { status: 'error' };
  }
};

export default apiClient;
