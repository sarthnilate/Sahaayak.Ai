import React, { useState } from 'react';
import {
  Radio, Send, Upload, RefreshCw, Search, Filter, AlertCircle, CheckCircle,
  FileText, Globe, MapPin, Eye, Sparkles, X
} from 'lucide-react';
import { Report } from '../../types';
import { submitReport, retryReport } from '../../services/api';
import { StatusBadge } from '../common/StatusBadge';

interface Props {
  reports: Report[];
  onRefresh: () => void;
  isLoading: boolean;
}

export const ReportsView: React.FC<Props> = ({ reports, onRefresh, isLoading }) => {
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
      setSubmitSuccess(`Report submitted & processed successfully (ID: ${created.id.slice(0, 8)})`);
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
    try {
      const updated = await retryReport(reportId);
      setSelectedReport(updated);
      onRefresh();
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    } finally {
      setIsRetrying(false);
    }
  };

  const filteredReports = reports.filter((r) => {
    if (statusFilter !== 'all' && r.processing_status !== statusFilter) return false;
    if (langFilter !== 'all' && r.input_language !== langFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = r.original_text.toLowerCase().includes(q);
      const matchLoc = (r.location_claim || '').toLowerCase().includes(q);
      const matchSummary = (r.extracted_json?.summary || '').toLowerCase().includes(q);
      if (!matchText && !matchLoc && !matchSummary) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      
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
            Google Gemini Powered Extraction • Multilingual EN / हिंदी / मराठी
          </span>
        </div>

        {/* 1-Click Simulation Presets */}
        <div className="mb-4">
          <p className="text-[11px] font-mono uppercase text-[#A7A7A7] mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#D4FF3F]" />
            Fast Demo Injection Presets (Click to Load):
          </p>
          <div className="flex flex-wrap gap-2">
            {presets.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyPreset(preset)}
                className="px-2.5 py-1 rounded bg-[#1D1D1D] hover:bg-[#282828] text-xs font-mono text-white border border-[#333] hover:border-[#FF2DA8] transition-all"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-[#A7A7A7] mb-1">
              REPORT CONTENT / CITIZEN OBSERVATION *
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Describe what you see: water depth, blocked streets, fallen trees, stranded commuters (English, Hindi, or Marathi)..."
              rows={3}
              className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg p-3 text-sm text-white placeholder-[#555] outline-none transition-colors"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-mono text-[#A7A7A7] mb-1">
                LOCATION CLAIM / LANDMARK
              </label>
              <input
                type="text"
                value={locationClaim}
                onChange={(e) => setLocationClaim(e.target.value)}
                placeholder="e.g. Hindmata Flyover, Dadar"
                className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg px-3 py-2 text-xs text-white placeholder-[#555] outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-[#A7A7A7] mb-1">
                LANGUAGE DETECTED / REPORTED
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg px-3 py-2 text-xs text-white outline-none"
              >
                <option value="en">English (EN)</option>
                <option value="hi">हिंदी (Hindi)</option>
                <option value="mr">मराठी (Marathi)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono text-[#A7A7A7] mb-1">
                ATTACH PHOTO / PROOF (OPTIONAL)
              </label>
              <label className="w-full bg-[#0B0B0B] border border-dashed border-[#282828] hover:border-[#FF2DA8] rounded-lg px-3 py-2 text-xs text-[#A7A7A7] cursor-pointer flex items-center justify-center gap-2 truncate transition-colors">
                <Upload className="w-3.5 h-3.5 text-[#FF2DA8]" />
                <span className="truncate">{selectedFile ? selectedFile.name : 'Upload JPG/PNG'}</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {submitError && (
            <div className="p-2.5 rounded-lg bg-[#351316] border border-[#FF5C68]/40 text-xs text-[#FF5C68] flex items-center gap-2 font-mono">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{submitError}</span>
            </div>
          )}

          {submitSuccess && (
            <div className="p-2.5 rounded-lg bg-[#10291F] border border-[#48C78E]/40 text-xs text-[#48C78E] flex items-center gap-2 font-mono">
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span>{submitSuccess}</span>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-lg text-xs font-bold font-mono bg-[#FF2DA8] hover:bg-[#E91E93] text-white shadow-[0_0_15px_rgba(255,45,168,0.35)] transition-all flex items-center gap-2"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'EXTRACTING WITH AI...' : 'SUBMIT & NORMALIZE REPORT'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Reports Feed Header & Filters */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-[#D4FF3F]" />
          <h3 className="font-bold text-sm text-white font-mono uppercase tracking-wide">
            Intake Archive ({filteredReports.length} Reports)
          </h3>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#A7A7A7] absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search reports or landmarks..."
              className="bg-[#151515] border border-[#282828] focus:border-[#FF2DA8] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#666] outline-none"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#151515] border border-[#282828] rounded-lg px-2.5 py-1.5 text-xs font-mono text-[#A7A7A7] outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="processed">Processed</option>
            <option value="needs_review">Needs Review</option>
            <option value="failed">Failed</option>
          </select>

          {/* Language Filter */}
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
          filteredReports.map((report) => (
            <div
              key={report.id}
              onClick={() => setSelectedReport(report)}
              className="bg-[#151515] border border-[#282828] hover:border-[#FF2DA8]/50 rounded-xl p-4 sm:p-5 transition-all cursor-pointer group hover:bg-[#191919]"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge status={report.processing_status} />
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded uppercase font-bold bg-[#1E1E1E] text-[#D4FF3F] border border-[#333]">
                    {report.input_language}
                  </span>
                  <span className="text-[11px] font-mono text-[#A7A7A7]">
                    Source: {report.extraction_source === 'gemini' ? 'Google Gemini' : 'Demo Adapter'}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-[#A7A7A7]">
                  {new Date(report.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {report.reporter_name || 'Citizen'}
                </span>
              </div>

              <p className="text-sm text-white mb-2 font-medium">
                "{report.original_text}"
              </p>

              {report.extracted_json && (
                <div className="p-2.5 rounded-lg bg-[#0B0B0B] border border-[#222] text-xs font-mono text-[#D4FF3F] space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-[#A7A7A7]">
                    <span>STRUCTURED SUMMARY:</span>
                    <span>Confidence: {(report.extracted_json.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-white text-xs">{report.extracted_json.summary}</p>
                </div>
              )}

              <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#222] text-xs font-mono text-[#A7A7A7]">
                <span className="flex items-center gap-1.5 truncate">
                  <MapPin className="w-3.5 h-3.5 text-[#FF2DA8]" />
                  {report.location_claim || report.extracted_json?.location_name || 'Location Not Specified'}
                </span>
                <span className="text-[#FF2DA8] font-bold group-hover:underline flex items-center gap-1 shrink-0">
                  <Eye className="w-3.5 h-3.5" />
                  INSPECT EXTRACTION &rarr;
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Report Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#151515] border border-[#FF2DA8]/40 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-[0_0_30px_rgba(255,45,168,0.2)] space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-[#282828]">
              <div className="flex items-center gap-2">
                <StatusBadge status={selectedReport.processing_status} />
                <h3 className="text-base font-bold text-white font-mono">
                  Report #{selectedReport.id.slice(0, 8)}
                </h3>
              </div>
              <button
                onClick={() => setSelectedReport(null)}
                className="p-1 rounded-lg bg-[#1E1E1E] text-[#A7A7A7] hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Original Submission */}
            <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono text-[#A7A7A7]">
                <span className="uppercase font-bold text-[#FF2DA8]">Original User Input</span>
                <span>Language: {selectedReport.input_language}</span>
              </div>
              <p className="text-sm text-white italic">
                "{selectedReport.original_text}"
              </p>
              <div className="text-[11px] font-mono text-[#A7A7A7] pt-1">
                Reporter: {selectedReport.reporter_name} • Location claim: {selectedReport.location_claim || 'None'}
              </div>
            </div>

            {/* AI Extracted Structured Fields */}
            {selectedReport.extracted_json ? (
              <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-[#222]">
                  <span className="uppercase font-bold text-[#D4FF3F] flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Structured Extraction (Pydantic Validated)
                  </span>
                  <span className="text-[#A7A7A7]">
                    Confidence: {(selectedReport.extracted_json.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-[#A7A7A7] block text-[10px]">HAZARD TYPE:</span>
                    <span className="text-white font-bold">{selectedReport.extracted_json.hazard_type}</span>
                  </div>
                  <div>
                    <span className="text-[#A7A7A7] block text-[10px]">SEVERITY:</span>
                    <span className="text-[#FF2DA8] font-bold uppercase">{selectedReport.extracted_json.severity}</span>
                  </div>
                  <div>
                    <span className="text-[#A7A7A7] block text-[10px]">WATER DEPTH:</span>
                    <span className="text-white">{selectedReport.extracted_json.water_depth_cm ? `${selectedReport.extracted_json.water_depth_cm} cm` : 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-[#A7A7A7] block text-[10px]">GROUNDED COORDS:</span>
                    <span className={selectedReport.extracted_json.has_grounded_coordinates ? 'text-[#48C78E]' : 'text-[#F5B942]'}>
                      {selectedReport.extracted_json.has_grounded_coordinates ? 'Confirmed Grounded' : 'Approximate / None'}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[#A7A7A7] block text-[10px] mb-1">AFFECTED INFRASTRUCTURE:</span>
                  <div className="flex flex-wrap gap-1">
                    {selectedReport.extracted_json.affected_infrastructure?.map((item, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-[#1D1D1D] text-white text-[11px] border border-[#333]">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <span className="text-[#A7A7A7] block text-[10px] mb-1">URGENT NEEDS DETECTED:</span>
                  <div className="flex flex-wrap gap-1">
                    {selectedReport.extracted_json.urgent_needs?.map((need, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-[#252B12] text-[#D4FF3F] text-[11px] border border-[#D4FF3F]/30">
                        {need}
                      </span>
                    ))}
                  </div>
                </div>

                {selectedReport.extracted_json._fallback_to_demo && (
                  <div className="p-2 rounded bg-[#30240D] text-[#F5B942] text-[11px]">
                    Live provider returned: "{selectedReport.extracted_json._provider_error}". Report was safely preserved and extracted via Demo Adapter.
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-[#351316] border border-[#FF5C68]/30 text-xs text-[#FF5C68] font-mono">
                No extraction output available. Error: {selectedReport.error_message || 'Processing incomplete'}.
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-[#282828]">
              <button
                onClick={() => handleRetry(selectedReport.id)}
                disabled={isRetrying}
                className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#1D1D1D] hover:bg-[#282828] text-[#D4FF3F] border border-[#D4FF3F]/30 flex items-center gap-2"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
                <span>{isRetrying ? 'RE-EXTRACTING...' : 'RETRY EXTRACTION'}</span>
              </button>

              <button
                onClick={() => setSelectedReport(null)}
                className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#282828] hover:bg-[#333] text-white"
              >
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
