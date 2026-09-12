import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { sendCopilotMessageApi } from '../../services/api';
import { applyCopilotCorrections } from './complaintFormSlice';

export const sendCopilotMessage = createAsyncThunk(
  'copilot/sendMessage',
  async ({ userMessage }, { getState, dispatch, rejectWithValue }) => {
    try {
      const { fields } = getState().complaintForm;
      const { messages } = getState().copilot;
      
      const response = await sendCopilotMessageApi(fields, userMessage, messages);
      
      // Dispatch corrections to update complaint form fields and trigger animation
      dispatch(applyCopilotCorrections(response));
      
      return response;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

const copilotSlice = createSlice({
  name: 'copilot',
  initialState: {
    messages: [
      {
        id: 'welcome-1',
        sender: 'copilot',
        text: '👋 Welcome to AIVOA Copilot! I am your AI Quality Assistant for pharmaceutical complaints. Paste a complaint, upload a PDF document, or ask me to correct any fields.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ],
    isThinking: false,
    error: null
  },
  reducers: {
    addUserMessage: (state, action) => {
      state.messages.push({
        id: `user-${Date.now()}`,
        sender: 'user',
        text: action.payload,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });
    },
    clearCopilotChat: (state) => {
      state.messages = [
        {
          id: 'welcome-1',
          sender: 'copilot',
          text: '👋 Welcome to AIVOA Copilot! I am your AI Quality Assistant for pharmaceutical complaints. Paste a complaint, upload a PDF document, or ask me to correct any fields.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ];
      state.isThinking = false;
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendCopilotMessage.pending, (state) => {
        state.isThinking = true;
        state.error = null;
      })
      .addCase(sendCopilotMessage.fulfilled, (state, action) => {
        state.isThinking = false;
        const { copilot_reply, modified_field_keys } = action.payload;
        state.messages.push({
          id: `copilot-${Date.now()}`,
          sender: 'copilot',
          text: copilot_reply,
          modifiedFields: modified_field_keys,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
      })
      .addCase(sendCopilotMessage.rejected, (state, action) => {
        state.isThinking = false;
        state.error = action.payload;
        state.messages.push({
          id: `error-${Date.now()}`,
          sender: 'copilot',
          text: `⚠️ Error: ${action.payload || 'Failed to process message.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
      });
  }
});

export const { addUserMessage, clearCopilotChat } = copilotSlice.actions;
export default copilotSlice.reducer;
