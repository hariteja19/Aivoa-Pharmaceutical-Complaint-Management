import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const processTextComplaintApi = async (text) => {
  const response = await apiClient.post('/complaints/process', { text });
  return response.data;
};

export const uploadComplaintDocApi = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post('/complaints/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const sendCopilotMessageApi = async (argsOrFields, maybeUserMsg, maybeChatHistory = []) => {
  let payload;
  if (typeof argsOrFields === 'object' && argsOrFields !== null && 'userMessage' in argsOrFields) {
    payload = {
      current_fields: argsOrFields.currentFields || {},
      user_message: argsOrFields.userMessage || '',
      chat_history: argsOrFields.chatHistory || [],
      document_text: argsOrFields.documentText || null,
      document_name: argsOrFields.documentName || null,
      extracted_fields: argsOrFields.extractedFields || {}
    };
  } else {
    payload = {
      current_fields: argsOrFields || {},
      user_message: maybeUserMsg || '',
      chat_history: maybeChatHistory || []
    };
  }
  const response = await apiClient.post('/copilot/chat', payload);
  return response.data;
};

export const createComplaintRecordApi = async (complaintData) => {
  const response = await apiClient.post('/complaints', complaintData);
  return response.data;
};

export const generateEmailDraftApi = async (complaintData) => {
  const response = await apiClient.post('/complaints/email-draft', complaintData);
  return response.data;
};

export const fetchComplaintsListApi = async (params = {}) => {
  const response = await apiClient.get('/complaints', { params });
  return response.data;
};

export const fetchComplaintByIdApi = async (id) => {
  const response = await apiClient.get(`/complaints/${id}`);
  return response.data;
};

export const deleteComplaintApi = async (id) => {
  await apiClient.delete(`/complaints/${id}`);
};

export default apiClient;
