import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { fetchComplaintsListApi, fetchComplaintByIdApi, deleteComplaintApi } from '../../services/api';

export const fetchComplaintsList = createAsyncThunk(
  'complaintsList/fetchList',
  async (params, { rejectWithValue }) => {
    try {
      const data = await fetchComplaintsListApi(params);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

export const fetchComplaintById = createAsyncThunk(
  'complaintsList/fetchById',
  async (id, { rejectWithValue }) => {
    try {
      const data = await fetchComplaintByIdApi(id);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

export const deleteComplaint = createAsyncThunk(
  'complaintsList/delete',
  async (complaintId, { dispatch, rejectWithValue }) => {
    try {
      await deleteComplaintApi(complaintId);
      // Re-fetch list immediately after deletion
      dispatch(fetchComplaintsList({ search: '', severity: 'ALL' }));
      return complaintId;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

const complaintsListSlice = createSlice({
  name: 'complaintsList',
  initialState: {
    items: [],
    total: 0,
    selectedComplaint: null,
    status: 'idle',
    error: null,
    filters: {
      search: '',
      severity: 'ALL'
    }
  },
  reducers: {
    setFilterSearch: (state, action) => {
      state.filters.search = action.payload;
    },
    setFilterSeverity: (state, action) => {
      state.filters.severity = action.payload;
    },
    clearSelectedComplaint: (state) => {
      state.selectedComplaint = null;
    },
    resetFilters: (state) => {
      state.filters.search = '';
      state.filters.severity = 'ALL';
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchComplaintsList.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(fetchComplaintsList.fulfilled, (state, action) => {
        state.status = 'idle';
        state.items = action.payload.items || [];
        state.total = action.payload.total || 0;
      })
      .addCase(fetchComplaintsList.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      })
      .addCase(fetchComplaintById.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(fetchComplaintById.fulfilled, (state, action) => {
        state.status = 'idle';
        state.selectedComplaint = action.payload;
      })
      .addCase(fetchComplaintById.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      });
  }
});

export const { setFilterSearch, setFilterSeverity, clearSelectedComplaint, resetFilters } = complaintsListSlice.actions;
export default complaintsListSlice.reducer;
