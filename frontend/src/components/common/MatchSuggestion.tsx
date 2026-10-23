import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  Link2,
  PlusCircle,
  FileText,
  MapPin,
  Clock,
  Layers,
  Copy,
  ShieldAlert,
} from 'lucide-react';
import { Report, MatchCandidate } from '../../types';
import { ConfirmActionDialog } from './ConfirmActionDialog';

interface MatchSuggestionProps {
  report: Report;
  candidate: MatchCandidate;
  onConfirm: (incidentId: string, reportId: string, notes: string) => Promise<void>;
  onReject: (incidentId: string, reportId: string, notes: string) => Promise<void>;
  onCreateNewIncident: (reportId: string, notes: string) => Promise<void>;
}

export const MatchSuggestion: React.FC<MatchSuggestionProps> = ({
  report,
  candidate,
  onConfirm,
  onReject,
  onCreateNewIncident,
}) => {
  const [activeDialog, setActiveDialog] = useState<'confirm' | 'reject' | 'create_incident' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  const renderBandBadge = (band: string) => {
    switch (band.toLowerCase()) {
      case 'strong':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
            <span>Strong Match</span>
          </span>
        );
      case 'possible':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-950/80 text-amber-300 border border-amber-500/40">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
            <span>Possible Match</span>
          </span>
        );
      case 'weak':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-zinc-800 text-zinc-300 border border-zinc-700">
            <HelpCircle className="w-3.5 h-3.5 text-zinc-400" aria-hidden="true" />
            <span>Weak Match</span>
          </span>
        );
    }
  };

  const handleConfirmAction = async (action: 'confirm' | 'reject' | 'create_incident', notes: string) => {
    setIsSubmitting(true);
    try {
      if (action === 'confirm') {
        await onConfirm(candidate.incident_id, report.id, notes);
        setActionFeedback('Match confirmed successfully. Report linked.');
      } else if (action === 'reject') {
        await onReject(candidate.incident_id, report.id, notes);
        setActionFeedback('Suggestion rejected. Will not be re-suggested unless inputs change.');
      } else if (action === 'create_incident') {
        await onCreateNewIncident(report.id, notes);
        setActionFeedback('New incident created from this report.');
      }
    } catch (err: any) {
      setActionFeedback(`Error: ${err.message || 'Operation failed'}`);
    } finally {
      setIsSubmitting(false);
      setActiveDialog(null);
    }
  };

  return (
    <div className="bg-[#141416] border border-zinc-800 rounded-xl p-5 shadow-lg space-y-5">
      {/* Header bar: Band + Origin badge + Status */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-zinc-800">
        <div className="flex items-center gap-2.5">
          {renderBandBadge(candidate.band)}
          <span className="text-xs text-zinc-400 font-mono">
            Candidate Incident: #{candidate.incident_id.slice(0, 12)}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {candidate.is_same_origin && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-medium bg-purple-950/70 text-purple-300 border border-purple-500/30">
              <Copy className="w-3 h-3" aria-hidden="true" />
              <span>Copied Claim / Same Origin</span>
            </span>
          )}
          {candidate.existing_link_status && (
            <span
              className={`px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wider ${
                candidate.existing_link_status === 'confirmed'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : candidate.existing_link_status === 'rejected'
                  ? 'bg-rose-950 text-rose-400 border border-rose-800'
                  : 'bg-zinc-800 text-zinc-300'
              }`}
            >
              Link Status: {candidate.existing_link_status}
            </span>
          )}
        </div>
      </div>

      {actionFeedback && (
        <div className="p-3 text-xs rounded-lg bg-zinc-900 border border-indigo-500/30 text-indigo-300 flex items-center justify-between">
          <span>{actionFeedback}</span>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-zinc-400 hover:text-zinc-200"
          >
            ×
          </button>
        </div>
      )}

      {/* Side-by-Side Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Source Report */}
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5" aria-hidden="true" />
              Source Report #{report.id.slice(0, 8)}
            </span>
            <span className="text-xs text-zinc-500 uppercase font-mono">
              Lang: {report.input_language || 'en'}
            </span>
          </div>

          <p className="text-sm text-zinc-200 leading-relaxed bg-black/40 p-3 rounded border border-zinc-800/80 italic">
            "{report.original_text}"
          </p>

          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <div className="flex items-center gap-1.5 text-zinc-400">
              <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" aria-hidden="true" />
              <span className="truncate">
                {report.location_claim || report.extracted_json?.reported_location_text || 'No location text'}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-zinc-400">
              <Clock className="w-3.5 h-3.5 text-zinc-500 shrink-0" aria-hidden="true" />
              <span>{new Date(report.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
          </div>

          <div className="text-xs text-zinc-500 flex items-center justify-between pt-1 border-t border-zinc-800/50">
            <span>Category: <strong className="text-zinc-300">{report.extracted_json?.category || 'unknown'}</strong></span>
            {report.coordinates_lat ? (
              <span className="text-emerald-400">Coords grounded</span>
            ) : (
              <span className="text-zinc-500">Coords ungrounded</span>
            )}
          </div>
        </div>

        {/* Right: Candidate Incident */}
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5" aria-hidden="true" />
              Target Incident #{candidate.incident_id.slice(0, 8)}
            </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 capitalize">
              {candidate.incident_category}
            </span>
          </div>

          <div className="bg-black/40 p-3 rounded border border-zinc-800/80 space-y-1">
            <h4 className="text-sm font-semibold text-zinc-100">{candidate.incident_title}</h4>
            <div className="flex items-center gap-1.5 text-xs text-zinc-400">
              <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" aria-hidden="true" />
              <span>{candidate.incident_location}</span>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-zinc-400 pt-1">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-zinc-500" aria-hidden="true" />
              <span>Created {new Date(candidate.incident_created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <span className="text-xs text-zinc-500 font-mono">
              Evaluation pure & deterministic
            </span>
          </div>

          <div className="p-2 rounded bg-zinc-950/60 border border-zinc-800 text-xs text-zinc-300">
            <strong className="text-zinc-400 block mb-0.5">Rationale:</strong>
            {candidate.rationale}
          </div>
        </div>
      </div>

      {/* Structured Signals: For, Against, and Unknowns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
        {/* Signals For */}
        <div className="bg-zinc-900/50 border border-emerald-900/30 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
            <CheckCircle2 className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Signals FOR Match ({candidate.signals_for.length})</span>
          </div>
          <ul className="space-y-1.5">
            {candidate.signals_for.map((sig, idx) => (
              <li key={idx} className="text-xs text-zinc-300 flex items-start gap-1.5">
                <span className="text-emerald-500 font-bold shrink-0">•</span>
                <div>
                  <span className="font-semibold text-zinc-200 capitalize">{sig.name.replace('_', ' ')}:</span>{' '}
                  <span className="text-zinc-400">{sig.detail}</span>
                </div>
              </li>
            ))}
            {candidate.signals_for.length === 0 && (
              <li className="text-xs text-zinc-500 italic">No positive signals</li>
            )}
          </ul>
        </div>

        {/* Signals Against / Hard Negatives */}
        <div className="bg-zinc-900/50 border border-rose-900/30 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-400">
            <XCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Signals AGAINST / Contra ({candidate.signals_against.length})</span>
          </div>
          <ul className="space-y-1.5">
            {candidate.signals_against.map((sig, idx) => (
              <li key={idx} className="text-xs text-zinc-300 flex items-start gap-1.5">
                <span className="text-rose-500 font-bold shrink-0">•</span>
                <div>
                  <span className="font-semibold text-zinc-200 capitalize">{sig.name.replace('_', ' ')}:</span>{' '}
                  <span className="text-zinc-400">{sig.detail}</span>
                </div>
              </li>
            ))}
            {candidate.signals_against.length === 0 && (
              <li className="text-xs text-zinc-500 italic">No counter signals</li>
            )}
          </ul>
        </div>

        {/* Unknowns / Missing Information */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-300">
            <HelpCircle className="w-4 h-4 text-zinc-400 shrink-0" aria-hidden="true" />
            <span>Unknowns / Epistemic Gaps ({candidate.unknowns.length})</span>
          </div>
          <ul className="space-y-1.5">
            {candidate.unknowns.map((unk, idx) => (
              <li key={idx} className="text-xs text-zinc-400 flex items-start gap-1.5">
                <span className="text-zinc-500 font-bold shrink-0">?</span>
                <span>{unk}</span>
              </li>
            ))}
            {candidate.unknowns.length === 0 && (
              <li className="text-xs text-zinc-500 italic">All signals verified</li>
            )}
          </ul>
        </div>
      </div>

      {/* Action Controls for Coordinator */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-zinc-800">
        <div className="text-xs text-zinc-500">
          Audited coordinator decision. Never silently merges or deletes data.
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setActiveDialog('create_incident')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-amber-300 bg-amber-950/60 hover:bg-amber-900/80 border border-amber-600/40 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <PlusCircle className="w-3.5 h-3.5" aria-hidden="true" />
            Create New Incident
          </button>

          <button
            type="button"
            onClick={() => setActiveDialog('reject')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-300 bg-rose-950/60 hover:bg-rose-900/80 border border-rose-600/40 transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500"
          >
            <XCircle className="w-3.5 h-3.5" aria-hidden="true" />
            Reject Match
          </button>

          <button
            type="button"
            onClick={() => setActiveDialog('confirm')}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-emerald-200 bg-emerald-700 hover:bg-emerald-600 border border-emerald-500 shadow transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-400"
          >
            <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
            Confirm Link
          </button>
        </div>
      </div>

      {/* Accessible Action Dialogs */}
      {activeDialog === 'confirm' && (
        <ConfirmActionDialog
          isOpen={true}
          title="Confirm Duplicate Match"
          description={`Link Report #${report.id.slice(0, 8)} to Incident #${candidate.incident_id.slice(0, 8)} (${candidate.incident_title})? The report will be associated as corroborating evidence without rewriting or altering original text.`}
          actionType="confirm"
          confirmLabel="Confirm Link"
          placeholderNotes="e.g. Verified Marathi phrasing refers to the same waterlogged underpass."
          isLoading={isSubmitting}
          onConfirm={(notes) => handleConfirmAction('confirm', notes)}
          onCancel={() => setActiveDialog(null)}
        />
      )}

      {activeDialog === 'reject' && (
        <ConfirmActionDialog
          isOpen={true}
          title="Reject Duplicate Suggestion"
          description={`Reject match between Report #${report.id.slice(0, 8)} and Incident #${candidate.incident_id.slice(0, 8)}? This link will not be suggested again unless the report content or incident details are updated.`}
          actionType="reject"
          confirmLabel="Reject Match"
          placeholderNotes="e.g. False positive: localized tree fall on eastern connector, separate from main bridge."
          isLoading={isSubmitting}
          onConfirm={(notes) => handleConfirmAction('reject', notes)}
          onCancel={() => setActiveDialog(null)}
        />
      )}

      {activeDialog === 'create_incident' && (
        <ConfirmActionDialog
          isOpen={true}
          title="Create New Incident from Report"
          description={`Create an independent new incident from unmatched Report #${report.id.slice(0, 8)}? This keeps the report isolated and initiates a new crisis management workflow.`}
          actionType="create_incident"
          confirmLabel="Create Incident"
          placeholderNotes="e.g. Distinct localized hazard requiring separate dispatch."
          isLoading={isSubmitting}
          onConfirm={(notes) => handleConfirmAction('create_incident', notes)}
          onCancel={() => setActiveDialog(null)}
        />
      )}
    </div>
  );
};
