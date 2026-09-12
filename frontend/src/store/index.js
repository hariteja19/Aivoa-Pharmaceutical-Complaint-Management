import { configureStore } from '@reduxjs/toolkit';
import complaintFormReducer from './slices/complaintFormSlice';
import copilotReducer from './slices/copilotSlice';
import complaintsListReducer from './slices/complaintsListSlice';

export const store = configureStore({
  reducer: {
    complaintForm: complaintFormReducer,
    copilot: copilotReducer,
    complaintsList: complaintsListReducer
  }
});
