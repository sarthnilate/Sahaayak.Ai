import React, { useState, useEffect } from 'react';
import {
  Radio, Send, Upload, RefreshCw, Search, AlertCircle, CheckCircle,
  MapPin, Eye, Sparkles, X, Bot, AlertTriangle,
  HelpCircle, UserCheck, User, GitMerge
} from 'lucide-react';
import { Report, AiStatus, MatchCandidate, ReportMatchesResponse } from '../../types';
import {
  submitReport,
  retryReport,
  submitCoordinatorCorrection,
  getAiStatus,
  getReportImageUrl,
  createIncidentFromReport,
  getReportMatches,
  confirmReportMatch,
  rejectReportMatch
} from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { StatusBadge } from '../common/StatusBadge';
import { MatchSuggestion } from '../common/MatchSuggestion';

interface Props {
  reports: Report[];
  onRefresh: () => void;
  isLoading: boolean;
  onNavigateToIncident?: (incidentId: string) => void;
}

export const ReportsView: React.FC<Props> = ({ reports, onRefresh, isLoading, onNavigateToIncident }) => {
  const { hasRole } = useAuth();
  const [aiStatus, setAiStatus] = useState<AiStatus | null>(null);

  // Form state
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('en');
  const [locationClaim, setLocationClaim] = useState('');
  const [reporterName, setReporterName] = useState('Citizen Reporter');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('all');
  const [langFilter, setLangFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Detail Modal
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryMessage, setRetryMessage] = useState<string | null>(null);

  // Coordinator correction state
  const [correctionCategory, setCorrectionCategory] = useState('');
  const [correctionSeverity, setCorrectionSeverity] = useState('');
  const [correctionLocation, setCorrectionLocation] = useState('');
  const [correctionNotes, setCorrectionNotes] = useState('');
  const [isSubmittingCorrection, setIsSubmittingCorrection] = useState(false);
  const [correctionSuccess, setCorrectionSuccess] = useState<string | null>(null);
  const [correctionError, setCorrectionError] = useState<string | null>(null);

  // Promotion to incident state
  const [showPromoteModal, setShowPromoteModal] = useState(false);
  const [promoteTitle, setPromoteTitle] = useState('');
  const [promoteCategory, setPromoteCategory] = useState('waterlogging');
  const [promotePriority, setPromotePriority] = useState('medium');
  const [promoteDistrict, setPromoteDistrict] = useState('Mumbai City');
  const [isPromoting, setIsPromoting] = useState(false);
  const [promoteSuccessId, setPromoteSuccessId] = useState<string | null>(null);
  const [promoteError, setPromoteError] = useState<string | null>(null);

  // Phase 5 Matches State
  const [showMatchesModal, setShowMatchesModal] = useState(false);
  const [matchesData, setMatchesData] = useState<ReportMatchesResponse | null>(null);
  const [isLoadingMatches, setIsLoadingMatches] = useState(false);
  const [matchesError, setMatchesError] = useState<string | null>(null);

  const handleOpenMatches = async (report: Report) => {
    setIsLoadingMatches(true);
    setMatchesError(null);
    setShowMatchesModal(true);
    try {
      const resp = await getReportMatches(report.id);
      setMatchesData(resp);
    } catch (err: any) {
      setMatchesError(err.message || 'Failed to compute report duplicate matches');
    } finally {
      setIsLoadingMatches(false);
    }
  };

  const handleConfirmMatchFromModal = async (incidentId: string, reportId: string, notes: string) => {
    await confirmReportMatch(incidentId, reportId, notes);
    if (selectedReport) {
      const resp = await getReportMatches(selectedReport.id);
      setMatchesData(resp);
    }
    onRefresh();
  };

  const handleRejectMatchFromModal = async (incidentId: string, reportId: string, notes: string) => {
    await rejectReportMatch(incidentId, reportId, notes);
    if (selectedReport) {
      const resp = await getReportMatches(selectedReport.id);
      setMatchesData(resp);
    }
    onRefresh();
  };

  const handleCreateNewIncidentFromModal = async (reportId: string, notes: string) => {
    await createIncidentFromReport({
      report_id: reportId,
      district_source: 'coordinator_set'
    });
    setShowMatchesModal(false);
    onRefresh();
  };

  const handleOpenPromote = (report: Report) => {
    const ext = report.extracted_json || {};
    const loc = ext.reported_location_text || report.location_claim || 'Mumbai Ward';
    const summ = ext.short_summary || report.original_text.slice(0, 60);
    setPromoteTitle(`Incident: ${loc} - ${ext.category || 'Hazard'}`);
    setPromoteCategory(ext.category || 'waterlogging');
    setPromotePriority(ext.claimed_severity === 'critical' ? 'critical' : ext.claimed_severity === 'high' ? 'high' : 'medium');
    setPromoteDistrict(loc.toLowerCase().includes('suburban') || loc.toLowerCase().includes('bandra') || loc.toLowerCase().includes('andheri') ? 'Mumbai Suburban' : 'Mumbai City');
    setPromoteSuccessId(null);
    setPromoteError(null);
    setShowPromoteModal(true);
  };

  const handleConfirmPromote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReport) return;
    setIsPromoting(true);
    setPromoteError(null);
    try {
      const inc = await createIncidentFromReport({
        report_id: selectedReport.id,
        title: promoteTitle,
        category: promoteCategory,
        suggested_priority: promotePriority,
        district: promoteDistrict,
        district_source: 'coordinator_set'
      });
      setPromoteSuccessId(inc.id);
      onRefresh();
    } catch (err: any) {
      setPromoteError(err.message || 'Failed to promote report');
    } finally {
      setIsPromoting(false);
    }
  };

  useEffect(() => {
    getAiStatus()
      .then(setAiStatus)
      .catch(() => {
        // Fallback default
        setAiStatus({
          mode: 'demo',
          provider: 'deterministic-demo',
          model: 'demo-ruleset-v1',
          api_key_configured: false,
        });
      });
  }, []);

  const presets = [
    {
      label: 'Hindmata Bus (English)',
      text: 'Water is above knee level near Hindmata cinema flyover underpass. Buses are completely stuck and water is rising fast. Need help urgently!',
      lang: 'en',
      loc: 'Hindmata cinema underpass, Dadar',
      reporter: 'Aarav Sharma'
    },
    {
      label: 'दादर टीटी सर्कल (Hindi)',
      text: 'दादर टीटी सर्कल और हिंदमाता के पास 3 फीट पानी भर गया है, दुकानें और गाड़ियां डूब रही हैं। लोग फंसे हैं। मदद चाहिए।',
      lang: 'hi',
      loc: 'दादर टीटी सर्कल (Dadar TT Circle)',
      reporter: 'राजेश गुप्ता'
    },
    {
      label: 'हिंदमाता उड्डाणपूल (Marathi)',
      text: 'हिंदमाता फ्लायओव्हरखाली पाणी साचल्यामुळे वाहतूक ठप्प झाली आहे. बेस्ट बसेस मार्ग बदलण्यात आले आहेत. तातडीने पाण्याचा उपसा आवश्यक आहे.',
      lang: 'mr',
      loc: 'हिंदमाता उड्डाणपूल (Hindmata Flyover)',
      reporter: 'सुनील कदम'
    },
    {
      label: 'WEH Tree Block (English)',
      text: 'Huge tree has crashed on Western Express Highway right before Bandra flyover north side. Two lanes totally blocked, bumper-to-bumper traffic.',
      lang: 'en',
      loc: 'Western Express Highway near Bandra',
      reporter: 'Karan Malhotra'
    },
    {
      label: 'Forwarded Rumor (Dam Alert)',
      text: 'FORWARDED AS RECEIVED: Vihar dam gates have collapsed and massive flood wave heading towards Powai! Evacuate immediately!',
      lang: 'en',
      loc: 'Vihar Dam / Powai (Unverified claim)',
      reporter: 'WhatsApp Forward'
    }
  ];

  const handleApplyPreset = (p: typeof presets[0]) => {
    setText(p.text);
    setLanguage(p.lang);
    setLocationClaim(p.loc);
    setReporterName(p.reporter);
    setSubmitError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setSubmitError('Please enter report description text.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const formData = new FormData();
      formData.append('original_text', text);
      formData.append('input_language', language);
      formData.append('reporter_name', reporterName);
      if (locationClaim) formData.append('location_claim', locationClaim);
      if (selectedFile) formData.append('media_file', selectedFile);

      const created = await submitReport(formData);
      setSubmitSuccess(`Report submitted & processed successfully (Ref: ${created.reference_code || created.id.slice(0, 8)})`);
      setText('');
      setLocationClaim('');
      setSelectedFile(null);
      onRefresh();
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to submit report');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetry = async (reportId: string) => {
    setIsRetrying(true);
    setRetryMessage(null);
    try {
      const updated = await retryReport(reportId);
      setSelectedReport(updated);
      setRetryMessage(`Retry succeeded! Status: ${updated.processing_status}`);
      onRefresh();
    } catch (err: any) {
      setRetryMessage(`Retry failed: ${err.message}`);
    } finally {
      setIsRetrying(false);
    }
  };

  const handleCorrectionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReport) return;
    if (!correctionNotes.trim()) {
      setCorrectionError('Correction notes explaining the change are required.');
      return;
    }

    setIsSubmittingCorrection(true);
    setCorrectionError(null);
    setCorrectionSuccess(null);

    try {
      const updated = await submitCoordinatorCorrection(selectedReport.id, {
        corrected_category: correctionCategory || undefined,
        corrected_severity: correctionSeverity || undefined,
        corrected_location: correctionLocation || undefined,
        correction_notes: correctionNotes.trim(),
      });
      setSelectedReport(updated);
      setCorrectionSuccess('Coordinator correction successfully saved and audited!');
      setCorrectionNotes('');
      onRefresh();
    } catch (err: any) {
      setCorrectionError(err.message || 'Failed to save correction.');
    } finally {
      setIsSubmittingCorrection(false);
    }
  };

  const filteredReports = reports.filter((r) => {
    if (statusFilter !== 'all' && r.processing_status !== statusFilter) return false;
    if (langFilter !== 'all' && r.input_language !== langFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = r.original_text.toLowerCase().includes(q);
      const matchLoc = (r.location_claim || '').toLowerCase().includes(q);
      const matchSummary = (r.extracted_json?.short_summary || r.extracted_json?.summary || '').toLowerCase().includes(q);
      if (!matchText && !matchLoc && !matchSummary) return false;
    }
    return true;
  });

  const isDemoMode = (report: Report | null) => {
    if (report?.extraction_metadata?.mode === 'demo') return true;
    if (report?.extraction_source === 'deterministic-demo' || report?.extraction_source === 'demo') return true;
    return aiStatus?.mode === 'demo';
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: AI System Status */}
      <div className="bg-[#121212] border border-[#282828] rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#1E1E1E] text-[#D4FF3F]">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                AI Extraction Engine
              </span>
              {aiStatus?.mode === 'demo' ? (
                <span
                  data-testid="global-ai-mode-badge"
                  className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-[#D4FF3F]/15 text-[#D4FF3F] border border-[#D4FF3F]/40"
                >
                  DEMO MODE (simulated)
                </span>
              ) : (
                <span
                  data-testid="global-ai-mode-badge"
                  className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-[#FF2DA8]/15 text-[#FF2DA8] border border-[#FF2DA8]/40"
                >
                  LIVE GEMINI ({aiStatus?.model || 'gemini-2.5-flash'})
                </span>
              )}
            </div>
            <p className="text-[11px] font-mono text-[#A7A7A7]">
              Provider: {aiStatus?.provider || 'deterministic-demo'} • Model: {aiStatus?.model || 'demo-ruleset-v1'} • Key Configured: {aiStatus?.api_key_configured ? 'Yes' : 'No'}
            </p>
          </div>
        </div>
        <div className="text-[11px] font-mono text-[#777]">
          Untrusted input sanitized & schema-validated
        </div>
      </div>

      {/* Top Section: Quick Intake Form */}
      <div className="bg-[#151515] border border-[#282828] rounded-xl p-5 sm:p-6 shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 mb-4 border-b border-[#282828]">
          <div className="flex items-center gap-2">
            <Radio className="w-5 h-5 text-[#FF2DA8]" />
            <h3 className="text-base font-bold text-white font-mono uppercase tracking-wide">
              Submit Community Incident Report
            </h3>
          </div>
          <span className="text-xs font-mono text-[#A7A7A7]">
            Multilingual AI Intake • Auto-Extracted via {aiStatus?.mode === 'gemini' ? 'Gemini 2.5' : 'Deterministic Demo'}
          </span>
        </div>

        {/* Quick Presets */}
        <div className="mb-5">
          <label className="text-[11px] font-mono uppercase text-[#A7A7A7] block mb-2 font-bold tracking-wider">
            Test Scenarios / Quick Presets:
          </label>
          <div className="flex flex-wrap gap-2">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyPreset(p)}
                className="px-2.5 py-1 text-xs rounded-lg bg-[#1F1F1F] hover:bg-[#2A2A2A] text-white border border-[#333] transition-colors flex items-center gap-1.5"
              >
                <Sparkles className="w-3 h-3 text-[#D4FF3F]" />
                <span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-mono text-[#A7A7A7] block mb-1.5 font-bold">
              REPORT DETAILS (TEXT) *
            </label>
            <textarea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              lang={language}
              placeholder="Describe what happened, where, and what assistance is needed (Hindi, Marathi, or English)..."
              className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg p-3 text-sm text-white placeholder-[#555] outline-none transition-colors"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-mono text-[#A7A7A7] block mb-1">
                ORIGINAL LANGUAGE
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg p-2.5 text-xs font-mono text-white outline-none"
              >
                <option value="en">English (EN)</option>
                <option value="hi">हिंदी (Hindi - HI)</option>
                <option value="mr">मराठी (Marathi - MR)</option>
                <option value="mixed">Mixed Multilingual</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-mono text-[#A7A7A7] block mb-1">
                REPORTED LOCATION TEXT
              </label>
              <input
                type="text"
                value={locationClaim}
                onChange={(e) => setLocationClaim(e.target.value)}
                placeholder="e.g. Hindmata Cinema underpass"
                className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg p-2.5 text-xs text-white placeholder-[#555] outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-mono text-[#A7A7A7] block mb-1">
                REPORTER ATTRIBUTION
              </label>
              <input
                type="text"
                value={reporterName}
                onChange={(e) => setReporterName(e.target.value)}
                placeholder="Name or agency"
                className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg p-2.5 text-xs text-white placeholder-[#555] outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-mono text-[#A7A7A7] block mb-1">
              ATTACH EVIDENCE PHOTO (OPTIONAL)
            </label>
            <div className="flex items-center gap-3">
              <label className="cursor-pointer px-3 py-2 rounded-lg bg-[#0B0B0B] border border-[#282828] hover:border-[#FF2DA8] text-xs font-mono text-white flex items-center gap-2">
                <Upload className="w-3.5 h-3.5 text-[#FF2DA8]" />
                <span>{selectedFile ? selectedFile.name : 'Choose Image File'}</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
              </label>
              {selectedFile && (
                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="text-xs font-mono text-[#FF5C68] hover:underline"
                >
                  Clear file
                </button>
              )}
            </div>
          </div>

          {submitError && (
            <div className="p-3 rounded-lg bg-[#351316] border border-[#FF5C68]/40 text-[#FF5C68] text-xs font-mono flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{submitError}</span>
            </div>
          )}

          {submitSuccess && (
            <div className="p-3 rounded-lg bg-[#142A1E] border border-[#48C78E]/40 text-[#48C78E] text-xs font-mono flex items-center gap-2">
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span>{submitSuccess}</span>
            </div>
          )}

          <div className="flex items-center justify-end pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2.5 rounded-lg bg-[#FF2DA8] hover:bg-[#e02694] disabled:opacity-50 text-white font-mono font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-[0_0_15px_rgba(255,45,168,0.3)]"
            >
              <Send className={`w-3.5 h-3.5 ${isSubmitting ? 'animate-pulse' : ''}`} />
              <span>{isSubmitting ? 'Extracting via AI...' : 'Submit & Ingest'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Reports Header & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
        <div>
          <h2 className="text-lg font-bold text-white font-mono tracking-wide">
            Ingested Reports ({filteredReports.length})
          </h2>
          <p className="text-xs font-mono text-[#A7A7A7]">
            Chronological live intake with AI schema-level validation
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 sm:w-48">
            <Search className="w-3.5 h-3.5 text-[#777] absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search reports..."
              className="w-full bg-[#151515] border border-[#282828] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#777] outline-none"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#151515] border border-[#282828] rounded-lg px-2.5 py-1.5 text-xs font-mono text-[#A7A7A7] outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="processed">Processed</option>
            <option value="needs_review">Needs Review</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={langFilter}
            onChange={(e) => setLangFilter(e.target.value)}
            className="bg-[#151515] border border-[#282828] rounded-lg px-2.5 py-1.5 text-xs font-mono text-[#A7A7A7] outline-none"
          >
            <option value="all">All Languages</option>
            <option value="en">English (EN)</option>
            <option value="hi">हिंदी (HI)</option>
            <option value="mr">मराठी (MR)</option>
          </select>

          <button
            onClick={onRefresh}
            className="p-1.5 rounded-lg bg-[#151515] border border-[#282828] text-[#A7A7A7] hover:text-white"
            title="Refresh list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Reports List */}
      <div className="space-y-3">
        {filteredReports.length === 0 ? (
          <div className="bg-[#151515] border border-[#282828] rounded-xl p-8 text-center text-[#A7A7A7] text-xs font-mono">
            No reports matching active filters.
          </div>
        ) : (
          filteredReports.map((report) => {
            const demoFlag = isDemoMode(report);
            return (
              <div
                key={report.id}
                onClick={() => {
                  setSelectedReport(report);
                  setRetryMessage(null);
                  setCorrectionSuccess(null);
                  setCorrectionError(null);
                }}
                className="bg-[#151515] border border-[#282828] hover:border-[#FF2DA8]/50 rounded-xl p-4 sm:p-5 transition-all cursor-pointer group hover:bg-[#191919]"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={report.processing_status} />
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded uppercase font-bold bg-[#1E1E1E] text-[#D4FF3F] border border-[#333]">
                      {report.input_language}
                    </span>
                    {demoFlag ? (
                      <span
                        data-testid="report-demo-badge"
                        className="text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold bg-[#D4FF3F]/15 text-[#D4FF3F] border border-[#D4FF3F]/40 flex items-center gap-1"
                      >
                        <Bot className="w-3 h-3" />
                        DEMO MODE (simulated)
                      </span>
                    ) : (
                      <span
                        data-testid="report-gemini-badge"
                        className="text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold bg-[#FF2DA8]/15 text-[#FF2DA8] border border-[#FF2DA8]/40 flex items-center gap-1"
                      >
                        <Sparkles className="w-3 h-3" />
                        LIVE GEMINI
                      </span>
                    )}
                    {report.coordinator_correction && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded uppercase font-bold bg-[#48C78E]/15 text-[#48C78E] border border-[#48C78E]/40">
                        Coordinator Corrected
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] font-mono text-[#A7A7A7]">
                    {new Date(report.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {report.reporter_name || 'Citizen'}
                  </span>
                </div>

                <p
                  className="text-sm text-white mb-2 font-medium"
                  lang={report.input_language || 'en'}
                >
                  "{report.original_text}"
                </p>

                {report.extracted_json && (
                  <div className="p-2.5 rounded-lg bg-[#0B0B0B] border border-[#222] text-xs font-mono text-[#D4FF3F] space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-[#A7A7A7]">
                      <span className="uppercase font-bold text-[#FF2DA8]">
                        Category: {report.extracted_json.category || report.extracted_json.hazard_type || 'Unknown'} | Severity: {report.extracted_json.claimed_severity || report.extracted_json.severity || 'Unknown'}
                      </span>
                      <span>
                        {report.extraction_metadata ? `${report.extraction_metadata.latency_ms}ms` : ''}
                      </span>
                    </div>
                    <p className="text-white text-xs">
                      {report.extracted_json.short_summary || report.extracted_json.summary || 'Summary pending'}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#222] text-xs font-mono text-[#A7A7A7]">
                  <span className="flex items-center gap-1.5 truncate">
                    <MapPin className="w-3.5 h-3.5 text-[#FF2DA8]" />
                    {report.location_claim || report.extracted_json?.reported_location_text || 'Location Not Specified'}
                  </span>
                  <span className="text-[#FF2DA8] font-bold group-hover:underline flex items-center gap-1 shrink-0">
                    <Eye className="w-3.5 h-3.5" />
                    INSPECT EXTRACTION &rarr;
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Report Detail Modal (Dual Column Layout with Phase 3 Schema) */}
      {selectedReport && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="report-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md overflow-y-auto"
        >
          <div className="bg-[#151515] border border-[#FF2DA8]/40 rounded-2xl w-full max-w-5xl my-8 max-h-[90vh] overflow-y-auto p-5 sm:p-7 shadow-[0_0_35px_rgba(255,45,168,0.25)] space-y-6">
            
            {/* Modal Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#282828]">
              <div className="flex items-center gap-2.5 flex-wrap">
                <StatusBadge status={selectedReport.processing_status} />
                <h3 id="report-modal-title" className="text-base font-bold text-white font-mono">
                  Report #{selectedReport.reference_code || selectedReport.id.slice(0, 8)}
                </h3>

                {isDemoMode(selectedReport) ? (
                  <span
                    data-testid="detail-demo-badge"
                    className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-[#D4FF3F]/15 text-[#D4FF3F] border border-[#D4FF3F]/40"
                  >
                    <Bot className="w-3.5 h-3.5" />
                    DEMO MODE (simulated)
                  </span>
                ) : (
                  <span
                    data-testid="detail-gemini-badge"
                    className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-[#FF2DA8]/15 text-[#FF2DA8] border border-[#FF2DA8]/40"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    LIVE GEMINI ({selectedReport.extraction_metadata?.model || 'gemini-2.5-flash'})
                  </span>
                )}

                {selectedReport.extraction_metadata && (
                  <span className="text-[11px] font-mono text-[#A7A7A7]">
                    Latency: {selectedReport.extraction_metadata.latency_ms}ms • Attempts: {selectedReport.attempt_count || selectedReport.extraction_metadata.attempt_count || 1}
                  </span>
                )}
              </div>

              <button
                onClick={() => setSelectedReport(null)}
                aria-label="Close report details"
                className="p-1.5 rounded-lg bg-[#1E1E1E] text-[#A7A7A7] hover:text-white transition-colors self-end sm:self-auto"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error / Failure Explanation banner with aria-live */}
            {(selectedReport.processing_status === 'failed' || selectedReport.error_message) && (
              <div
                role="alert"
                aria-live="polite"
                className="p-4 rounded-xl bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68] space-y-1.5"
              >
                <div className="flex items-center gap-2 font-bold uppercase">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#FF5C68]" />
                  <span>Extraction Failure Detected</span>
                </div>
                <p className="text-white text-xs">
                  {selectedReport.error_message || 'Domain extraction provider error encountered.'}
                </p>
                <p className="text-[11px] text-[#A7A7A7]">
                  The original report content has been safely preserved in the database. Use the button below to retry extraction.
                </p>
              </div>
            )}

            {/* Dual Column Layout: Left (Reported) vs Right (Extracted) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
              
              {/* LEFT COLUMN: "Reported (by the person)" */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b border-[#262626]">
                  <User className="w-4 h-4 text-[#FF2DA8]" />
                  <h4 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                    Reported (by the person)
                  </h4>
                </div>

                <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-3">
                  <div className="flex items-center justify-between text-xs font-mono text-[#A7A7A7]">
                    <span className="uppercase font-bold text-[#FF2DA8]">Citizen Message</span>
                    <span className="px-2 py-0.5 rounded bg-[#1D1D1D] text-[#D4FF3F] text-[11px]">
                      Language: {selectedReport.input_language.toUpperCase()}
                    </span>
                  </div>

                  {/* Hindi/Marathi/English text with proper lang attribute */}
                  <p
                    className="text-white text-sm leading-relaxed p-3 rounded-lg bg-[#151515] border border-[#222] font-medium"
                    lang={selectedReport.input_language || 'en'}
                  >
                    "{selectedReport.original_text}"
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                    <div>
                      <span className="text-[#777] block text-[10px]">SUBMISSION TIME:</span>
                      <span className="text-white text-[11px]">
                        {new Date(selectedReport.submitted_at).toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="text-[#777] block text-[10px]">REPORTER NAME:</span>
                      <span className="text-white text-[11px]">
                        {selectedReport.reporter_name || 'Anonymous Citizen'}
                      </span>
                    </div>
                    <div>
                      <span className="text-[#777] block text-[10px]">LOCATION CLAIM:</span>
                      <span className="text-white text-[11px]">
                        {selectedReport.location_claim || 'Not specified'}
                      </span>
                    </div>
                    <div>
                      <span className="text-[#777] block text-[10px]">FORWARDED CHAIN:</span>
                      <span className={selectedReport.extracted_json?.is_forwarded_message ? 'text-[#F5B942]' : 'text-[#48C78E]'}>
                        {selectedReport.extracted_json?.is_forwarded_message ? 'Yes (Forwarded Alert)' : 'Direct Witness Report'}
                      </span>
                    </div>
                  </div>

                  {/* Image preview if attached */}
                  {selectedReport.media_path && (
                    <div className="pt-2 border-t border-[#222]">
                      <span className="text-[10px] font-mono text-[#777] uppercase block mb-1.5">
                        Uploaded Media Evidence:
                      </span>
                      <img
                        src={getReportImageUrl(selectedReport.id)}
                        alt="Citizen uploaded incident evidence"
                        className="w-full max-h-56 object-cover rounded-lg border border-[#282828]"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                    </div>
                  )}
                </div>

                {/* Coordinator Correction View (if previously corrected) */}
                {selectedReport.coordinator_correction && (
                  <div className="p-4 rounded-xl bg-[#0E1A14] border border-[#48C78E]/40 space-y-2 font-mono text-xs">
                    <div className="flex items-center gap-1.5 text-[#48C78E] font-bold text-xs uppercase">
                      <UserCheck className="w-4 h-4" />
                      <span>Coordinator Override (Stored Separately)</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      {selectedReport.coordinator_correction.corrected_category && (
                        <div>
                          <span className="text-[#777] block text-[10px]">CORRECTED CATEGORY:</span>
                          <span className="text-white font-bold">{selectedReport.coordinator_correction.corrected_category}</span>
                        </div>
                      )}
                      {selectedReport.coordinator_correction.corrected_severity && (
                        <div>
                          <span className="text-[#777] block text-[10px]">CORRECTED SEVERITY:</span>
                          <span className="text-[#FF2DA8] font-bold uppercase">{selectedReport.coordinator_correction.corrected_severity}</span>
                        </div>
                      )}
                      {selectedReport.coordinator_correction.corrected_location && (
                        <div>
                          <span className="text-[#777] block text-[10px]">CORRECTED LOCATION:</span>
                          <span className="text-white">{selectedReport.coordinator_correction.corrected_location}</span>
                        </div>
                      )}
                    </div>
                    <div>
                      <span className="text-[#777] block text-[10px]">CORRECTION NOTES:</span>
                      <p className="text-white italic text-[11px] bg-[#070D0A] p-2 rounded border border-[#183325]">
                        "{selectedReport.coordinator_correction.correction_notes}"
                      </p>
                    </div>
                    <div className="text-[10px] text-[#777] pt-1">
                      Audited change by {selectedReport.corrected_by || 'Coordinator'} at {selectedReport.corrected_at ? new Date(selectedReport.corrected_at).toLocaleString() : 'Recent'}
                    </div>
                  </div>
                )}

                {/* Coordinator Correction Form (for coordinator/admin roles) */}
                {hasRole('coordinator', 'admin') && (
                  <div className="p-4 rounded-xl bg-[#121212] border border-[#282828] space-y-3 font-mono text-xs">
                    <div className="flex items-center gap-1.5 text-white font-bold text-xs uppercase">
                      <UserCheck className="w-4 h-4 text-[#FF2DA8]" />
                      <span>Add / Update Coordinator Correction</span>
                    </div>
                    <form onSubmit={handleCorrectionSubmit} className="space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] text-[#A7A7A7] block mb-1">Override Category</label>
                          <select
                            value={correctionCategory}
                            onChange={(e) => setCorrectionCategory(e.target.value)}
                            className="w-full bg-[#0B0B0B] border border-[#333] rounded p-1.5 text-xs text-white outline-none"
                          >
                            <option value="">Keep Extracted</option>
                            <option value="waterlogging">Waterlogging</option>
                            <option value="tree_fall">Tree Fall</option>
                            <option value="traffic_congestion">Traffic Congestion</option>
                            <option value="structural_damage">Structural Damage</option>
                            <option value="power_outage">Power Outage</option>
                            <option value="medical_emergency">Medical Emergency</option>
                            <option value="fire">Fire</option>
                            <option value="rumor">Rumor</option>
                            <option value="other">Other</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-[10px] text-[#A7A7A7] block mb-1">Override Severity</label>
                          <select
                            value={correctionSeverity}
                            onChange={(e) => setCorrectionSeverity(e.target.value)}
                            className="w-full bg-[#0B0B0B] border border-[#333] rounded p-1.5 text-xs text-white outline-none"
                          >
                            <option value="">Keep Extracted</option>
                            <option value="critical">Critical</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                            <option value="unknown">Unknown</option>
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="text-[10px] text-[#A7A7A7] block mb-1">Override Grounded Location</label>
                        <input
                          type="text"
                          value={correctionLocation}
                          onChange={(e) => setCorrectionLocation(e.target.value)}
                          placeholder="e.g. Verified Dadar TT Underpass"
                          className="w-full bg-[#0B0B0B] border border-[#333] rounded p-1.5 text-xs text-white placeholder-[#555] outline-none"
                        />
                      </div>

                      <div>
                        <label className="text-[10px] text-[#A7A7A7] block mb-1">Audit Notes * (Required)</label>
                        <textarea
                          rows={2}
                          value={correctionNotes}
                          onChange={(e) => setCorrectionNotes(e.target.value)}
                          placeholder="Explain coordinator rationale for this annotation..."
                          className="w-full bg-[#0B0B0B] border border-[#333] rounded p-1.5 text-xs text-white placeholder-[#555] outline-none"
                          required
                        />
                      </div>

                      {correctionError && (
                        <div className="text-[11px] text-[#FF5C68] font-mono">{correctionError}</div>
                      )}
                      {correctionSuccess && (
                        <div className="text-[11px] text-[#48C78E] font-mono">{correctionSuccess}</div>
                      )}

                      <button
                        type="submit"
                        disabled={isSubmittingCorrection}
                        className="px-3 py-1.5 rounded bg-[#222] hover:bg-[#333] text-white border border-[#444] font-bold text-[11px] uppercase tracking-wider"
                      >
                        {isSubmittingCorrection ? 'Saving...' : 'Save Annotation'}
                      </button>
                    </form>
                  </div>
                )}
              </div>

              {/* RIGHT COLUMN: AI Extracted, Inferred, Unknown & Follow-up */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b border-[#262626]">
                  <Sparkles className="w-4 h-4 text-[#D4FF3F]" />
                  <h4 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                    AI Structured Analysis
                  </h4>
                </div>

                {selectedReport.extracted_json ? (
                  <div className="space-y-4 font-mono text-xs">
                    
                    {/* 1. EXTRACTED BY AI */}
                    <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-3">
                      <div className="flex items-center justify-between border-b border-[#222] pb-2">
                        <span className="uppercase font-bold text-[#D4FF3F] flex items-center gap-1.5">
                          Extracted by AI
                        </span>
                        <span className="text-[10px] text-[#A7A7A7]">Directly Grounded Facts</span>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <span className="text-[#777] block text-[10px]">CATEGORY:</span>
                          <span className="text-white font-bold uppercase">
                            {selectedReport.extracted_json.category || selectedReport.extracted_json.hazard_type || 'unknown'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#777] block text-[10px]">CLAIMED SEVERITY:</span>
                          <span className="text-[#FF2DA8] font-bold uppercase">
                            {selectedReport.extracted_json.claimed_severity || selectedReport.extracted_json.severity || 'unknown'}
                          </span>
                        </div>
                      </div>

                      <div>
                        <span className="text-[#777] block text-[10px] mb-0.5">SHORT SUMMARY:</span>
                        <p className="text-white text-xs bg-[#121212] p-2.5 rounded border border-[#222]">
                          {selectedReport.extracted_json.short_summary || selectedReport.extracted_json.summary || 'N/A'}
                        </p>
                      </div>

                      {/* Location Precision & Source */}
                      <div className="grid grid-cols-2 gap-2 text-[11px] bg-[#121212] p-2 rounded border border-[#222]">
                        <div>
                          <span className="text-[#777] block text-[10px]">LOCATION TEXT:</span>
                          <span className="text-white truncate block">
                            {selectedReport.extracted_json.reported_location_text || 'None detected'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#777] block text-[10px]">PRECISION / SOURCE:</span>
                          <span className="text-white">
                            {selectedReport.extracted_json.location_precision || 'unknown'} / {selectedReport.extracted_json.location_source || 'unspecified'}
                          </span>
                        </div>
                      </div>

                      {/* Explicit Facts */}
                      <div>
                        <span className="text-[#777] block text-[10px] mb-1">EXPLICIT FACTS (FROM REPORT):</span>
                        {selectedReport.extracted_json.explicit_facts && selectedReport.extracted_json.explicit_facts.length > 0 ? (
                          <ul className="space-y-1">
                            {selectedReport.extracted_json.explicit_facts.map((fact, idx) => (
                              <li key={idx} className="flex items-start gap-1.5 text-white text-[11px]">
                                <span className="text-[#D4FF3F] font-bold">•</span>
                                <span>{fact}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-[#555] text-[11px] italic">No explicit bullet facts recorded</span>
                        )}
                      </div>

                      {/* People or Infrastructure Affected */}
                      {selectedReport.extracted_json.people_or_infrastructure_affected && selectedReport.extracted_json.people_or_infrastructure_affected.length > 0 && (
                        <div>
                          <span className="text-[#777] block text-[10px] mb-1">PEOPLE / INFRASTRUCTURE AFFECTED:</span>
                          <div className="flex flex-wrap gap-1">
                            {selectedReport.extracted_json.people_or_infrastructure_affected.map((item, idx) => (
                              <span key={idx} className="px-2 py-0.5 rounded bg-[#1D1D1D] text-white text-[11px] border border-[#333]">
                                {item}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* 2. INFERRED BY AI */}
                    <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-3">
                      <div className="flex items-center justify-between border-b border-[#222] pb-2">
                        <span className="uppercase font-bold text-[#FF2DA8] flex items-center gap-1.5">
                          Inferred by AI
                        </span>
                        <span className="text-[10px] text-[#A7A7A7]">Derived Predictions</span>
                      </div>

                      {/* Safety Concern */}
                      <div className="p-2.5 rounded-lg bg-[#18111B] border border-[#FF2DA8]/30">
                        <div className="flex items-center justify-between text-[11px] mb-1">
                          <span className="text-[#A7A7A7] font-bold">SAFETY CONCERN:</span>
                          <span className={selectedReport.extracted_json.safety_concern ? 'text-[#FF5C68] font-bold' : 'text-[#48C78E]'}>
                            {selectedReport.extracted_json.safety_concern ? 'ACTIVE THREAT DETECTED' : 'NO THREAT DETECTED'}
                          </span>
                        </div>
                        {selectedReport.extracted_json.safety_concern_reason && (
                          <p className="text-white text-[11px] italic">
                            "{selectedReport.extracted_json.safety_concern_reason}"
                          </p>
                        )}
                      </div>

                      {/* Model Inferences */}
                      <div>
                        <span className="text-[#777] block text-[10px] mb-1">MODEL INFERENCES:</span>
                        {selectedReport.extracted_json.model_inferences && selectedReport.extracted_json.model_inferences.length > 0 ? (
                          <ul className="space-y-1">
                            {selectedReport.extracted_json.model_inferences.map((inf, idx) => (
                              <li key={idx} className="flex items-start gap-1.5 text-white text-[11px]">
                                <span className="text-[#FF2DA8] font-bold">&rarr;</span>
                                <span>{inf}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-[#555] text-[11px] italic">No secondary inferences generated</span>
                        )}
                      </div>
                    </div>

                    {/* 3. UNKNOWN / MISSING */}
                    <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-2.5">
                      <div className="flex items-center justify-between border-b border-[#222] pb-2">
                        <span className="uppercase font-bold text-[#F5B942] flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Unknown / Missing
                        </span>
                        <span className="text-[10px] text-[#A7A7A7]">Gaps & Ambiguities</span>
                      </div>

                      {/* Missing Information */}
                      <div>
                        <span className="text-[#777] block text-[10px] mb-1">MISSING INFORMATION:</span>
                        {selectedReport.extracted_json.missing_information && selectedReport.extracted_json.missing_information.length > 0 ? (
                          <ul className="space-y-1">
                            {selectedReport.extracted_json.missing_information.map((m, idx) => (
                              <li key={idx} className="flex items-start gap-1.5 text-white text-[11px]">
                                <span className="text-[#F5B942] font-bold">?</span>
                                <span>{m}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-[#555] text-[11px] italic">None identified</span>
                        )}
                      </div>

                      {/* Ambiguities & Contradictions */}
                      {(selectedReport.extracted_json.ambiguities?.length || selectedReport.extracted_json.contradictions?.length) ? (
                        <div className="space-y-1.5 pt-1">
                          {selectedReport.extracted_json.ambiguities && selectedReport.extracted_json.ambiguities.length > 0 && (
                            <div>
                              <span className="text-[#777] block text-[10px]">AMBIGUITIES:</span>
                              <p className="text-white text-[11px]">
                                {selectedReport.extracted_json.ambiguities.join(', ')}
                              </p>
                            </div>
                          )}
                          {selectedReport.extracted_json.contradictions && selectedReport.extracted_json.contradictions.length > 0 && (
                            <div>
                              <span className="text-[#777] block text-[10px]">CONTRADICTIONS:</span>
                              <p className="text-[#FF5C68] text-[11px]">
                                {selectedReport.extracted_json.contradictions.join(', ')}
                              </p>
                            </div>
                          )}
                        </div>
                      ) : null}
                    </div>

                    {/* 4. NEEDS FOLLOW-UP */}
                    <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-2.5">
                      <div className="flex items-center justify-between border-b border-[#222] pb-2">
                        <span className="uppercase font-bold text-[#48C78E] flex items-center gap-1.5">
                          <HelpCircle className="w-3.5 h-3.5" />
                          Needs Follow-Up
                        </span>
                        <span className="text-[10px] text-[#A7A7A7]">Recommended Inquiries</span>
                      </div>

                      {selectedReport.extracted_json.follow_up_questions && selectedReport.extracted_json.follow_up_questions.length > 0 ? (
                        <ul className="space-y-1.5">
                          {selectedReport.extracted_json.follow_up_questions.map((q, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-white text-[11px] bg-[#121212] p-2 rounded border border-[#222]">
                              <span className="text-[#48C78E] font-bold font-mono">Q{idx + 1}:</span>
                              <span>{q}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-[#555] text-[11px] italic">No immediate follow-up required</span>
                      )}
                    </div>

                  </div>
                ) : (
                  <div className="p-6 rounded-xl bg-[#121212] border border-[#282828] text-center text-[#A7A7A7] text-xs font-mono space-y-2">
                    <p>No structured extraction is available for this report.</p>
                    <p className="text-[11px]">Status: {selectedReport.processing_status}. Try clicking Retry Extraction below.</p>
                  </div>
                )}

              </div>
            </div>

            {/* Modal Actions & Retry Button */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-4 border-t border-[#282828]">
              <div className="flex items-center gap-3 flex-wrap">
                <button
                  type="button"
                  data-testid="retry-button"
                  aria-live="polite"
                  onClick={() => handleRetry(selectedReport.id)}
                  disabled={isRetrying}
                  className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#1D1D1D] hover:bg-[#282828] text-[#D4FF3F] border border-[#D4FF3F]/30 disabled:opacity-50 flex items-center gap-2 transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
                  <span>{isRetrying ? 'RE-EXTRACTING VIA AI...' : 'RETRY EXTRACTION'}</span>
                </button>

                {hasRole('coordinator', 'admin') && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleOpenMatches(selectedReport)}
                      className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#1A1A22] hover:bg-[#252533] text-amber-300 border border-amber-500/40 shadow flex items-center gap-1.5 transition-all"
                    >
                      <GitMerge className="w-3.5 h-3.5 text-amber-400" />
                      <span>CHECK MATCHES</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleOpenPromote(selectedReport)}
                      className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white shadow-[0_0_12px_rgba(255,45,168,0.25)] flex items-center gap-1.5 transition-all"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>PROMOTE TO INCIDENT</span>
                    </button>
                  </>
                )}

                {retryMessage && (
                  <span
                    role="status"
                    aria-live="polite"
                    className="text-xs font-mono text-white"
                  >
                    {retryMessage}
                  </span>
                )}
              </div>

              <button
                type="button"
                onClick={() => setSelectedReport(null)}
                className="px-5 py-2 rounded-lg text-xs font-mono font-bold bg-[#282828] hover:bg-[#333] text-white transition-colors"
              >
                CLOSE
              </button>
            </div>

          </div>
        </div>
      )}

      {/* Duplicate Matches Modal (Phase 5 Explainable Baseline) */}
      {showMatchesModal && selectedReport && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="matches-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md overflow-y-auto"
        >
          <div className="bg-[#121214] border border-amber-500/40 rounded-2xl w-full max-w-5xl my-8 max-h-[90vh] overflow-y-auto p-5 sm:p-7 shadow-[0_0_35px_rgba(245,185,66,0.15)] space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-amber-950/60 border border-amber-500/30">
                  <GitMerge className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h3 id="matches-modal-title" className="text-base font-bold text-white font-mono">
                    Duplicate Candidates for Report #{selectedReport.reference_code || selectedReport.id.slice(0, 8)}
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Deterministic cross-lingual signal evaluation without embeddings or probabilistic guesses.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowMatchesModal(false)}
                className="p-1.5 rounded-lg bg-zinc-800 text-zinc-400 hover:text-white"
                aria-label="Close matches modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {isLoadingMatches && (
              <div className="py-12 text-center text-xs font-mono text-zinc-400 flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                <span>Evaluating lexicon tokens, location bounds, and temporal windows...</span>
              </div>
            )}

            {matchesError && (
              <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-500/40 text-xs font-mono text-rose-300">
                {matchesError}
              </div>
            )}

            {!isLoadingMatches && matchesData && matchesData.matches.length === 0 && (
              <div className="p-8 text-center text-xs font-mono text-zinc-400 bg-zinc-950/50 border border-zinc-800 rounded-xl space-y-3">
                <p>No active incidents matched this report's category or temporal window.</p>
                <button
                  onClick={() => {
                    setShowMatchesModal(false);
                    handleOpenPromote(selectedReport);
                  }}
                  className="px-4 py-2 rounded-lg text-xs font-bold font-mono bg-amber-600 hover:bg-amber-500 text-white"
                >
                  Create New Incident from this Report &rarr;
                </button>
              </div>
            )}

            {!isLoadingMatches && matchesData && matchesData.matches.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs font-mono text-zinc-400 pb-1">
                  <span>Found {matchesData.total_candidates} candidate incident(s) ranked by band</span>
                  {matchesData.origin_group_id && (
                    <span className="text-purple-300">Origin Group: #{matchesData.origin_group_id.slice(0, 8)}</span>
                  )}
                </div>

                {matchesData.matches.map((cand) => (
                  <MatchSuggestion
                    key={cand.incident_id}
                    report={selectedReport}
                    candidate={cand}
                    onConfirm={handleConfirmMatchFromModal}
                    onReject={handleRejectMatchFromModal}
                    onCreateNewIncident={handleCreateNewIncidentFromModal}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Promote to Incident Modal */}
      {showPromoteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#151515] border border-[#FF2DA8] rounded-2xl w-full max-w-md p-6 space-y-4 shadow-[0_0_35px_rgba(255,45,168,0.3)]">
            <div className="flex items-center justify-between pb-2 border-b border-[#282828]">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[#FF2DA8]" />
                <h3 className="text-sm font-bold text-white font-mono uppercase">
                  Promote Report #{selectedReport?.reference_code || selectedReport?.id.slice(0, 8)} to Incident
                </h3>
              </div>
              <button onClick={() => setShowPromoteModal(false)} className="text-[#A7A7A7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {promoteSuccessId ? (
              <div className="p-4 rounded-xl bg-[#10291F] border border-[#48C78E]/50 text-xs font-mono text-[#48C78E] space-y-3">
                <p className="font-bold">✓ Incident Created Successfully!</p>
                <p className="text-white text-[11px]">
                  Assigned Incident ID: <strong className="text-[#D4FF3F]">{promoteSuccessId}</strong>
                </p>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    onClick={() => {
                      setShowPromoteModal(false);
                      setSelectedReport(null);
                      if (onNavigateToIncident) {
                        onNavigateToIncident(promoteSuccessId);
                      }
                    }}
                    className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#48C78E] text-black"
                  >
                    GO TO INCIDENTS
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleConfirmPromote} className="space-y-4">
                {promoteError && (
                  <div className="p-3 rounded-xl bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68]">
                    {promoteError}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-mono text-[#A7A7A7] mb-1">INCIDENT TITLE *</label>
                  <input
                    type="text"
                    value={promoteTitle}
                    onChange={(e) => setPromoteTitle(e.target.value)}
                    required
                    className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-xl p-2.5 text-xs text-white font-mono outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-mono text-[#A7A7A7] mb-1">CATEGORY</label>
                    <select
                      value={promoteCategory}
                      onChange={(e) => setPromoteCategory(e.target.value)}
                      className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2 text-xs text-white font-mono"
                    >
                      <option value="waterlogging">Waterlogging</option>
                      <option value="tree_fall">Tree Fall</option>
                      <option value="landslide">Landslide</option>
                      <option value="structural_damage">Structural Damage</option>
                      <option value="power_outage">Power Outage</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-[#A7A7A7] mb-1">PRIORITY</label>
                    <select
                      value={promotePriority}
                      onChange={(e) => setPromotePriority(e.target.value)}
                      className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2 text-xs text-white font-mono"
                    >
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-mono text-[#A7A7A7] mb-1">DISTRICT (ADMINISTRATIVE)</label>
                  <input
                    type="text"
                    value={promoteDistrict}
                    onChange={(e) => setPromoteDistrict(e.target.value)}
                    className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2 text-xs text-white font-mono"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowPromoteModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-mono bg-[#222] text-[#A7A7A7]"
                  >
                    CANCEL
                  </button>
                  <button
                    type="submit"
                    disabled={isPromoting}
                    className="px-5 py-2 rounded-xl text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white disabled:opacity-50"
                  >
                    {isPromoting ? 'PROMOTING...' : 'CONFIRM & PROMOTE'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

    </div>
  );
};
