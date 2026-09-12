import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import {
  processTextComplaintApi,
  uploadComplaintDocApi,
  createComplaintRecordApi,
  generateEmailDraftApi
} from '../../services/api';
import { fetchComplaintsList, resetFilters } from './complaintsListSlice';

const initialFields = {
  complaint_reference: '',
  complaint_number: '',
  complaint_source: '',
  customer_name: '',
  product_name: '',
  product_strength: '',
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
  severity_level: '',
  priority: ''
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
  async (_, { getState, dispatch, rejectWithValue }) => {
    try {
      const { fields, analysis, rawInputText, documentName } = getState().complaintForm;
      // Prioritize explicit current AI risk assessment over empty or stale values
      const resolvedSeverity = analysis.risk_assessment?.severity_level || fields.severity_level || 'Minor';
      const resolvedPriority = analysis.risk_assessment?.priority || fields.priority || 'Medium';
      const payload = {
        ...fields,
        product_strength_grade: fields.product_strength_grade || fields.product_strength || '',
        product_strength: fields.product_strength || fields.product_strength_grade || '',
        complaint_reference: fields.complaint_reference || fields.complaint_number || '',
        complaint_number: fields.complaint_number || fields.complaint_reference || '',
        raw_input_text: rawInputText,
        document_name: documentName,
        completeness_score: analysis.validation?.completeness_score || 0,
        is_complete: analysis.validation?.is_complete || false,
        missing_fields: analysis.validation?.missing_fields || [],
        severity_level: resolvedSeverity,
        priority: resolvedPriority,
        patient_risk_flag: analysis.risk_assessment?.patient_risk_flag || false,
        risk_rationale: analysis.risk_assessment?.rationale || '',
        is_possible_duplicate: analysis.duplicates?.is_possible_duplicate || false,
        duplicate_reasons: analysis.duplicates?.match_reasons || [],
        root_cause_recommendations: analysis.root_cause_recommendations || [],
        capa_recommendations: analysis.capa_recommendations || [],
        executive_summary: analysis.executive_summary || ''
      };
      console.log('[COPILOT DEBUG STEP 11 - API SUBMIT PAYLOAD]', payload);
      const result = await createComplaintRecordApi(payload);
      // Immediately reset filters and refresh the complaints directory list
      dispatch(resetFilters());
      dispatch(fetchComplaintsList({ search: '', severity: 'ALL' }));
      return result;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || err.message);
    }
  }
);

export const generateEmailDraft = createAsyncThunk(
  'complaintForm/generateEmailDraft',
  async (_, { getState, rejectWithValue }) => {
    try {
      const { fields, analysis, rawInputText, documentName } = getState().complaintForm;
      const payload = {
        ...fields,
        raw_input_text: rawInputText,
        document_name: documentName,
        completeness_score: analysis?.validation?.completeness_score,
        patient_risk_flag: analysis?.risk_assessment?.patient_risk_flag,
        risk_rationale: analysis?.risk_assessment?.rationale,
        is_possible_duplicate: analysis?.duplicates?.is_possible_duplicate,
        duplicate_reasons: analysis?.duplicates?.match_reasons || [],
        root_cause_recommendations: analysis?.root_cause_recommendations || [],
        capa_recommendations: analysis?.capa_recommendations || [],
        executive_summary: analysis?.executive_summary || ''
      };
      const result = await generateEmailDraftApi(payload);
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
      risk_assessment: { severity_level: '', patient_risk_flag: false, rationale: '' },
      duplicates: { is_possible_duplicate: false, matching_complaint_ids: [], match_reasons: [] },
      root_cause_recommendations: [],
      capa_recommendations: [],
      executive_summary: ''
    },
    emailDraft: {
      to: 'Quality Assurance Team',
      subject: '',
      body: '',
      generated: false,
      isGenerating: false,
      error: null
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
      const { updates, structured_fields, updated_fields, modified_field_keys, recalculated_analysis, is_new_complaint } = action.payload;
      
      // STEP 7: Log Redux update payload
      console.log('[COPILOT DEBUG STEP 7 - REDUX DISPATCH PAYLOAD]', action.payload);

      // Strip null/undefined/empty values from structured_fields BEFORE spreading.
      // The backend Pydantic model serializes ALL 16 fields (most null) into structured_fields.
      // Without this filter, Object.keys(changes) would be 16 — incorrectly triggering
      // the "new complaint" state reset for any single-field update.
      const cleanStructuredFields = {};
      if (structured_fields && typeof structured_fields === 'object') {
        Object.entries(structured_fields).forEach(([k, v]) => {
          if (v !== null && v !== undefined && v !== '') {
            cleanStructuredFields[k] = v;
          }
        });
      }

      const sourceObj = { ...cleanStructuredFields, ...(updates || {}), ...(updated_fields || {}) };
      const changes = { ...sourceObj };

      // Normalize canonical aliases
      if (changes.product_strength && !changes.product_strength_grade) {
        changes.product_strength_grade = changes.product_strength;
      } else if (changes.product_strength_grade && !changes.product_strength) {
        changes.product_strength = changes.product_strength_grade;
      }
      if (changes.severity && !changes.severity_level) {
        changes.severity_level = changes.severity;
      } else if (changes.severity_level && !changes.severity) {
        changes.severity = changes.severity_level;
      }
      
      // Never allow complaint_number into state.fields
      delete changes.complaint_number;

      // Blacklist guard: ensure conversational words or section headers never become batch_lot_number
      const BATCH_BLACKLIST = [
        'identification', 'batch identification', 'product & batch identification',
        'section', 'section 2', 'form', 'the form', 'from the form', 'chat', 'the chat',
        'document', 'the document', 'pdf', 'file', 'uploaded', 'unspecified', 'none', 'null',
        'unknown', 'left-side', 'the left-side', 'complaint', 'record',
        'had', 'was', 'were', 'have', 'has', 'with', 'from', 'that', 'this',
        'label', 'vial', 'vials', 'carton', 'cartons', 'details', 'origin'
      ];
      if (changes.batch_lot_number) {
        const bl = String(changes.batch_lot_number).toLowerCase().trim();
        if (BATCH_BLACKLIST.includes(bl) || (/^[a-z]+$/.test(bl) && bl.length <= 4)) {
          console.warn('[REDUX GUARD] Rejected invalid batch_lot_number:', changes.batch_lot_number);
          delete changes.batch_lot_number;
        }
      }

      // Guard: strip trailing section headers from string values
      Object.entries(changes).forEach(([key, val]) => {
        if (typeof val === 'string') {
          changes[key] = val.replace(/(?:[.\s;,-]+|\s+)SECTION\s*\d+.*$/i, '').replace(/(?:[.\s;,-]+|\s+)REQUESTED\s+ACTION.*$/i, '').trim();
        }
      });

      // Guard: strip prompt instructions from complaint_description if present
      if (changes.complaint_description) {
        let desc = String(changes.complaint_description);
        const markers = ['Please analyze this complaint', 'Please do TWO things', 'Important:', 'Determine the risk level', 'SECTION 1:', 'REQUESTED ACTION:', 'Keep the complaint details separate', 'Please fill the complaint form'];
        markers.forEach(marker => {
          if (desc.includes(marker)) {
            if (desc.includes('Complaint Description:')) {
              desc = desc.split('Complaint Description:')[1].trim();
            } else {
              desc = desc.split(marker)[0].trim();
            }
          }
        });
        changes.complaint_description = desc;
      }

      // Reset fields ONLY when the backend explicitly marks this as a new complaint intake.
      // DO NOT use Object.keys(changes).length >= 4 — that incorrectly triggers on single-field
      // updates because structured_fields (before null-filtering) can carry all 16 Pydantic fields.
      if (is_new_complaint) {
        state.fields = {
          complaint_reference: '',
          complaint_source: '',
          customer_name: '',
          product_name: '',
          product_strength: '',
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
          severity_level: '',
          priority: ''
        };
        state.analysis = {
          validation: { completeness_score: 0, missing_fields: [], is_complete: false },
          risk_assessment: { severity_level: '', patient_risk_flag: false, rationale: '' },
          root_cause_recommendations: [],
          capa_recommendations: [],
          executive_summary: '',
          duplicates: { is_possible_duplicate: false, matching_complaint_ids: [], match_reasons: [] }
        };
        state.submitStatus = 'idle';
      }


      // Requirement: Do NOT overwrite good existing values with empty/null/undefined/Unknown values
      const appliedKeys = [];
      Object.entries(changes).forEach(([key, val]) => {
        if (
          val !== null &&
          val !== undefined &&
          val !== '' &&
          String(val).toLowerCase() !== 'unknown' &&
          String(val).toLowerCase() !== 'not provided' &&
          String(val).toLowerCase() !== 'null' &&
          String(val).toLowerCase() !== 'none'
        ) {
          state.fields[key] = val;
          appliedKeys.push(key);
        }
      });
      
      // Mark updated keys for visual highlight animation
      const highlights = {};
      const keysToHighlight = (modified_field_keys && modified_field_keys.length > 0)
        ? [...modified_field_keys, ...appliedKeys]
        : appliedKeys;

      keysToHighlight.forEach(k => {
        highlights[k] = true;
      });
      state.highlightMap = highlights;

      if (changes.complaint_description && !state.rawInputText) {
        state.rawInputText = changes.complaint_description;
      }

      if (recalculated_analysis) {
        if (recalculated_analysis.validation) {
          state.analysis.validation = recalculated_analysis.validation;
        }
        if (recalculated_analysis.risk_assessment) {
          state.analysis.risk_assessment = recalculated_analysis.risk_assessment;
          const aiSeverity = recalculated_analysis.risk_assessment.severity_level || changes.severity_level || updates?.severity_level;
          if (aiSeverity) {
            state.fields.severity_level = aiSeverity;
            console.log('[REDUX] AI severity synced to fields.severity_level:', aiSeverity);
          }
          const aiPriority = recalculated_analysis.risk_assessment.priority || changes.priority || updates?.priority;
          if (aiPriority) {
            state.fields.priority = aiPriority;
          }
        }
        if (recalculated_analysis.root_cause_recommendations && (recalculated_analysis.root_cause_recommendations.length > 0 || is_new_complaint)) {
          state.analysis.root_cause_recommendations = recalculated_analysis.root_cause_recommendations;
        }
        if (recalculated_analysis.capa_recommendations && (recalculated_analysis.capa_recommendations.length > 0 || is_new_complaint)) {
          state.analysis.capa_recommendations = recalculated_analysis.capa_recommendations;
        }
        if (recalculated_analysis.executive_summary !== undefined) {
          if (recalculated_analysis.executive_summary || is_new_complaint) {
            state.analysis.executive_summary = recalculated_analysis.executive_summary;
          }
        }
        if (recalculated_analysis.duplicates) {
          state.analysis.duplicates = recalculated_analysis.duplicates;
        }
      }

      // STEP 8: Log Redux State after update
      console.log('[COPILOT DEBUG STEP 8 - REDUX STATE AFTER UPDATE]', JSON.parse(JSON.stringify(state)));
    },
    clearHighlights: (state) => {
      state.highlightMap = {};
    },
    updateEmailDraft: (state, action) => {
      const { to, subject, body } = action.payload;
      if (to !== undefined) state.emailDraft.to = to;
      if (subject !== undefined) state.emailDraft.subject = subject;
      if (body !== undefined) state.emailDraft.body = body;
    },
    clearEmailDraft: (state) => {
      state.emailDraft = {
        to: 'Quality Assurance Team',
        subject: '',
        body: '',
        generated: false,
        isGenerating: false,
        error: null
      };
    },
    resetComplaintForm: (state) => {
      state.fields = { ...initialFields };
      state.highlightMap = {};
      state.rawInputText = '';
      state.documentName = null;
      state.analysis = {
        validation: { completeness_score: 0, missing_fields: [], is_complete: false },
        risk_assessment: { severity_level: '', patient_risk_flag: false, rationale: '' },
        duplicates: { is_possible_duplicate: false, matching_complaint_ids: [], match_reasons: [] },
        root_cause_recommendations: [],
        capa_recommendations: [],
        executive_summary: ''
      };
      state.emailDraft = {
        to: 'Quality Assurance Team',
        subject: '',
        body: '',
        generated: false,
        isGenerating: false,
        error: null
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
        state.submitStatus = 'idle';
        state.fields = { ...initialFields };
        state.analysis = {
          validation: { completeness_score: 0, missing_fields: [], is_complete: false },
          risk_assessment: { severity_level: '', patient_risk_flag: false, rationale: '' },
          duplicates: { is_possible_duplicate: false, matching_complaint_ids: [], match_reasons: [] },
          root_cause_recommendations: [],
          capa_recommendations: [],
          executive_summary: ''
        };
      })
      .addCase(processTextComplaint.fulfilled, (state, action) => {
        state.status = 'idle';
        const data = action.payload;
        state.rawInputText = data.raw_input_text || '';
        state.documentName = data.document_filename || null;
        if (data.extracted_fields) {
          const ext = {};
          Object.entries(data.extracted_fields).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== '' && String(v).toLowerCase() !== 'null' && String(v).toLowerCase() !== 'none') {
              ext[k] = v;
            }
          });
          if (ext.product_strength_grade && !ext.product_strength) ext.product_strength = ext.product_strength_grade;
          if (ext.product_strength && !ext.product_strength_grade) ext.product_strength_grade = ext.product_strength;
          if (ext.complaint_number && !ext.complaint_reference) ext.complaint_reference = ext.complaint_number;
          if (ext.complaint_reference && !ext.complaint_number) ext.complaint_number = ext.complaint_reference;
          if (data.risk_assessment?.severity_level) ext.severity_level = data.risk_assessment.severity_level;
          if (data.risk_assessment?.priority) ext.priority = data.risk_assessment.priority;
          state.fields = { ...initialFields, ...ext };
        }
        state.analysis = {
          extracted_fields: data.extracted_fields || {},
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
        state.submitStatus = 'idle';
        state.fields = { ...initialFields };
        state.analysis = {
          validation: { completeness_score: 0, missing_fields: [], is_complete: false },
          risk_assessment: { severity_level: '', patient_risk_flag: false, rationale: '' },
          duplicates: { is_possible_duplicate: false, matching_complaint_ids: [], match_reasons: [] },
          root_cause_recommendations: [],
          capa_recommendations: [],
          executive_summary: ''
        };
      })
      .addCase(uploadComplaintDoc.fulfilled, (state, action) => {
        state.status = 'idle';
        const { filename, extracted_text, analysis } = action.payload;
        state.documentName = filename;
        state.rawInputText = extracted_text;
        if (analysis?.extracted_fields) {
          const ext = {};
          Object.entries(analysis.extracted_fields).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== '' && String(v).toLowerCase() !== 'null' && String(v).toLowerCase() !== 'none') {
              ext[k] = v;
            }
          });
          if (ext.product_strength_grade && !ext.product_strength) ext.product_strength = ext.product_strength_grade;
          if (ext.product_strength && !ext.product_strength_grade) ext.product_strength_grade = ext.product_strength;
          if (ext.complaint_number && !ext.complaint_reference) ext.complaint_reference = ext.complaint_number;
          if (ext.complaint_reference && !ext.complaint_number) ext.complaint_number = ext.complaint_reference;
          if (analysis.risk_assessment?.severity_level) ext.severity_level = analysis.risk_assessment.severity_level;
          if (analysis.risk_assessment?.priority) ext.priority = analysis.risk_assessment.priority;
          state.fields = { ...initialFields, ...ext };
        }
        state.analysis = {
          extracted_fields: analysis?.extracted_fields || {},
          validation: analysis?.validation || {},
          risk_assessment: analysis?.risk_assessment || {},
          duplicates: analysis?.duplicates || {},
          root_cause_recommendations: analysis?.root_cause_recommendations || [],
          capa_recommendations: analysis?.capa_recommendations || [],
          executive_summary: analysis?.executive_summary || ''
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
      })
      // generateEmailDraft
      .addCase(generateEmailDraft.pending, (state) => {
        state.emailDraft.isGenerating = true;
        state.emailDraft.error = null;
      })
      .addCase(generateEmailDraft.fulfilled, (state, action) => {
        state.emailDraft.isGenerating = false;
        state.emailDraft.to = action.payload.to || 'Quality Assurance Team';
        state.emailDraft.subject = action.payload.subject || '';
        state.emailDraft.body = action.payload.body || '';
        state.emailDraft.generated = true;
        state.emailDraft.error = null;
      })
      .addCase(generateEmailDraft.rejected, (state, action) => {
        state.emailDraft.isGenerating = false;
        state.emailDraft.error = action.payload;
      });
  }
});

export const {
  updateFormField,
  applyCopilotCorrections,
  clearHighlights,
  resetComplaintForm,
  updateEmailDraft,
  clearEmailDraft
} = complaintFormSlice.actions;
export default complaintFormSlice.reducer;
