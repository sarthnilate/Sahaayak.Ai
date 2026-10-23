import React, { useEffect, useRef, useState } from 'react';
import { X, AlertCircle, CheckCircle, HelpCircle } from 'lucide-react';

interface ConfirmActionDialogProps {
  isOpen: boolean;
  title: string;
  description: string;
  actionType: 'confirm' | 'reject' | 'create_incident';
  confirmLabel: string;
  cancelLabel?: string;
  placeholderNotes?: string;
  isLoading?: boolean;
  onConfirm: (notes: string) => void;
  onCancel: () => void;
}

export const ConfirmActionDialog: React.FC<ConfirmActionDialogProps> = ({
  isOpen,
  title,
  description,
  actionType,
  confirmLabel,
  cancelLabel = 'Cancel',
  placeholderNotes = 'Add coordinator notes or reasoning (optional)...',
  isLoading = false,
  onConfirm,
  onCancel,
}) => {
  const [notes, setNotes] = useState('');
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);
  const firstFocusableRef = useRef<HTMLButtonElement | null>(null);

  // Store previously focused element and trap focus
  useEffect(() => {
    if (isOpen) {
      previouslyFocusedElementRef.current = document.activeElement as HTMLElement;
      // Focus the dialog or first focusable element
      setTimeout(() => {
        firstFocusableRef.current?.focus();
      }, 50);
    } else {
      if (previouslyFocusedElementRef.current) {
        previouslyFocusedElementRef.current.focus();
      }
      setNotes('');
    }
  }, [isOpen]);

  // Handle Escape key and tab trapping
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
        return;
      }

      if (e.key === 'Tab' && dialogRef.current) {
        const focusables = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length === 0) return;

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const getActionColor = () => {
    switch (actionType) {
      case 'confirm':
        return 'bg-emerald-600 hover:bg-emerald-700 text-white';
      case 'reject':
        return 'bg-rose-600 hover:bg-rose-700 text-white';
      case 'create_incident':
        return 'bg-amber-600 hover:bg-amber-700 text-white';
      default:
        return 'bg-indigo-600 hover:bg-indigo-700 text-white';
    }
  };

  const getIcon = () => {
    switch (actionType) {
      case 'confirm':
        return <CheckCircle className="w-5 h-5 text-emerald-400" aria-hidden="true" />;
      case 'reject':
        return <AlertCircle className="w-5 h-5 text-rose-400" aria-hidden="true" />;
      case 'create_incident':
        return <HelpCircle className="w-5 h-5 text-amber-400" aria-hidden="true" />;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-desc"
        className="w-full max-w-lg bg-[#18181B] border border-zinc-800 rounded-xl shadow-2xl p-6 text-zinc-100 animate-in fade-in zoom-in-95 duration-150"
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-zinc-900 border border-zinc-800">
              {getIcon()}
            </div>
            <h2 id="confirm-dialog-title" className="text-lg font-semibold text-zinc-100">
              {title}
            </h2>
          </div>
          <button
            ref={firstFocusableRef}
            onClick={onCancel}
            disabled={isLoading}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p id="confirm-dialog-desc" className="text-sm text-zinc-300 mb-4 leading-relaxed">
          {description}
        </p>

        <div className="mb-5">
          <label htmlFor="coordinator-notes" className="block text-xs font-medium text-zinc-400 mb-1.5">
            Coordinator Review Notes (Audited)
          </label>
          <textarea
            id="coordinator-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={placeholderNotes}
            rows={3}
            disabled={isLoading}
            className="w-full px-3 py-2 text-sm bg-zinc-900/90 border border-zinc-700 rounded-lg text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
          />
          <p className="text-xs text-zinc-500 mt-1">
            Recorded in the audit log. Unmatched reports remain immutable.
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={() => onConfirm(notes)}
            disabled={isLoading}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-zinc-900 focus:ring-indigo-500 disabled:opacity-50 ${getActionColor()}`}
          >
            {isLoading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
