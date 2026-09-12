import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { processTextComplaintApi, uploadComplaintDocApi, createComplaintRecordApi } from '../../services/api';

const initialFields = {
  complaint_source: '',
  customer_name: '',
  product_name: '',
  product_strength_grade: '',
  batch_lot_number: '',
  affected_quantity: '',
  manufacturing_date: '',
  expiry_date: '',
  manufacturing_site: '',
  material_type: '',
  complaint_date: '',
  complaint_type: '',
  complaint_description: '',
  severity_level: 'Low',
  priority: 'Medium'
};

export const processTextComplaint = createAsyncThunk(
  'complaintForm/processText',
  async (text, { rejectWithValue }) => {
    try {
      const data = await processTextComplaintApi(text);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

export const uploadComplaintDoc = createAsyncThunk(
  'complaintForm/uploadDoc',
  async (file, { rejectWithValue }) => {
    try {
      const data = await uploadComplaintDocApi(file);
      return data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

export const submitComplaintRecord = createAsyncThunk(
  'complaintForm/submitRecord',
  async (_, { getState, rejectWithValue }) => {
    try {
      const { fields, analysis, rawInputText, documentName } = getState().complaintForm;
      const payload = {
        ...fields,
        raw_input_text: rawInputText,
        document_name: documentName,
        completeness_score: analysis.validation?.completeness_score || 0,
        is_complete: analysis.validation?.is_complete || false,
        missing_fields: analysis.validation?.missing_fields || [],
        severity_level: analysis.risk_assessment?.severity_level || 'Low',
        patient_risk_flag: analysis.risk_assessment?.patient_risk_flag || false,
        risk_rationale: analysis.risk_assessment?.rationale || '',
        is_possible_duplicate: analysis.duplicates?.is_possible_duplicate || false,
        duplicate_reasons: analysis.duplicates?.match_reasons || [],
        root_cause_recommendations: analysis.root_cause_recommendations || [],
        capa_recommendations: analysis.capa_recommendations || [],
        executive_summary: analysis.executive_summary || ''
      };
      const result = await createComplaintRecordApi(payload);
      return result;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

const complaintFormSlice = createSlice({
  name: 'complaintForm',
  initialState: {
    fields: { ...initialFields },
    highlightMap: {}, // e.g. { batch_lot_number: true }
    rawInputText: '',
    documentName: null,
    analysis: {
      validation: { completeness_score: 0, missing_fields: [], is_complete: false },
      risk_assessment: { severity_level: 'Low', patient_risk_flag: false, rationale: '' },
      duplicates: { is_possible_duplicate: false, matching_complaint_ids: [], match_reasons: [] },
      root_cause_recommendations: [],
      capa_recommendations: [],
      executive_summary: ''
    },
    status: 'idle', // 'idle' | 'analyzing' | 'submitted' | 'failed'
    submitStatus: 'idle',
    error: null
  },
  reducers: {
    updateFormField: (state, action) => {
      const { field, value } = action.payload;
      state.fields[field] = value;
    },
    applyCopilotCorrections: (state, action) => {
      const { updates, updated_fields, modified_field_keys, recalculated_analysis } = action.payload;
      const changes = updates || updated_fields || {};
      if (changes && Object.keys(changes).length > 0) {
        state.fields = { ...state.fields, ...changes };
      }
      
      // Mark updated keys for visual highlight animation
      const highlights = {};
      const keysToHighlight = (modified_field_keys && modified_field_keys.length > 0)
        ? modified_field_keys
        : Object.keys(changes);

      keysToHighlight.forEach(k => {
        highlights[k] = true;
      });
      state.highlightMap = highlights;

      if (recalculated_analysis) {
        if (recalculated_analysis.validation) {
          state.analysis.validation = recalculated_analysis.validation;
        }
        if (recalculated_analysis.risk_assessment) {
          state.analysis.risk_assessment = recalculated_analysis.risk_assessment;
        }
      }
    },
    clearHighlights: (state) => {
      state.highlightMap = {};
    },
    resetComplaintForm: (state) => {
      state.fields = { ...initialFields };
      state.highlightMap = {};
      state.rawInputText = '';
      state.documentName = null;
      state.analysis = {
        validation: { completeness_score: 0, missing_fields: [], is_complete: false },
        risk_assessment: { severity_level: 'Low', patient_risk_flag: false, rationale: '' },
        duplicates: { is_possible_duplicate: false, matching_complaint_ids: [], match_reasons: [] },
        root_cause_recommendations: [],
        capa_recommendations: [],
        executive_summary: ''
      };
      state.status = 'idle';
      state.submitStatus = 'idle';
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    builder
      // processTextComplaint
      .addCase(processTextComplaint.pending, (state) => {
        state.status = 'analyzing';
        state.error = null;
      })
      .addCase(processTextComplaint.fulfilled, (state, action) => {
        state.status = 'idle';
        const data = action.payload;
        state.rawInputText = data.raw_input_text || '';
        state.documentName = data.document_filename || null;
        if (data.extracted_fields) {
          state.fields = { ...initialFields, ...data.extracted_fields };
        }
        state.analysis = {
          validation: data.validation || {},
          risk_assessment: data.risk_assessment || {},
          duplicates: data.duplicates || {},
          root_cause_recommendations: data.root_cause_recommendations || [],
          capa_recommendations: data.capa_recommendations || [],
          executive_summary: data.executive_summary || ''
        };
      })
      .addCase(processTextComplaint.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      })
      // uploadComplaintDoc
      .addCase(uploadComplaintDoc.pending, (state) => {
        state.status = 'analyzing';
        state.error = null;
      })
      .addCase(uploadComplaintDoc.fulfilled, (state, action) => {
        state.status = 'idle';
        const { filename, extracted_text, analysis } = action.payload;
        state.documentName = filename;
        state.rawInputText = extracted_text;
        if (analysis.extracted_fields) {
          state.fields = { ...initialFields, ...analysis.extracted_fields };
        }
        state.analysis = {
          validation: analysis.validation || {},
          risk_assessment: analysis.risk_assessment || {},
          duplicates: analysis.duplicates || {},
          root_cause_recommendations: analysis.root_cause_recommendations || [],
          capa_recommendations: analysis.capa_recommendations || [],
          executive_summary: analysis.executive_summary || ''
        };
      })
      .addCase(uploadComplaintDoc.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
      })
      // submitComplaintRecord
      .addCase(submitComplaintRecord.pending, (state) => {
        state.submitStatus = 'submitting';
      })
      .addCase(submitComplaintRecord.fulfilled, (state) => {
        state.submitStatus = 'success';
      })
      .addCase(submitComplaintRecord.rejected, (state, action) => {
        state.submitStatus = 'failed';
        state.error = action.payload;
      });
  }
});

export const { updateFormField, applyCopilotCorrections, clearHighlights, resetComplaintForm } = complaintFormSlice.actions;
export default complaintFormSlice.reducer;
