import React, { useState, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { useAuth } from '../../contexts/AuthContext';
import { submitReport } from '../../services/api';
import {
  Send, Upload, X, MapPin, Clock, FileText, CheckCircle, AlertCircle,
  Loader2, Image as ImageIcon, Globe
} from 'lucide-react';

interface ReportFormData {
  original_text: string;
  location_text: string;
  input_language: string;
  reporter_name: string;
  reporter_contact: string;
}

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'हिन्दी (Hindi)' },
  { value: 'mr', label: 'मराठी (Marathi)' },
  { value: 'ta', label: 'தமிழ் (Tamil)' },
  { value: 'te', label: 'తెలుగు (Telugu)' },
  { value: 'bn', label: 'বাংলা (Bengali)' },
  { value: 'gu', label: 'ગુજરાતી (Gujarati)' },
  { value: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { value: 'ml', label: 'മലയാളം (Malayalam)' },
  { value: 'pa', label: 'ਪੰਜਾਬੀ (Punjabi)' },
  { value: 'ur', label: 'اردو (Urdu)' },
];

const MAX_TEXT_LENGTH = 5000;
const MAX_UPLOAD_MB = 10;

export const SubmitReportView: React.FC = () => {
  const { user } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<ReportFormData>({
    defaultValues: {
      original_text: '',
      location_text: '',
      input_language: 'en',
      reporter_name: user?.full_name || user?.username || '',
      reporter_contact: user?.email || '',
    },
  });

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<{ referenceCode: string; id: string } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const textValue = watch('original_text', '');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate type
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) {
      setSubmitError('Only JPEG, PNG, and WebP images are allowed.');
      return;
    }

    // Validate size
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setSubmitError(`Image must be smaller than ${MAX_UPLOAD_MB} MB.`);
      return;
    }

    setImageFile(file);
    setSubmitError(null);

    // Preview
    const reader = new FileReader();
    reader.onloadend = () => setImagePreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const onSubmit = async (data: ReportFormData) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitResult(null);

    try {
      const formData = new FormData();
      formData.append('original_text', data.original_text);
      if (data.location_text) formData.append('location_text', data.location_text);
      formData.append('input_language', data.input_language);
      if (data.reporter_name) formData.append('reporter_name', data.reporter_name);
      if (data.reporter_contact) formData.append('reporter_contact', data.reporter_contact);
      if (imageFile) formData.append('image', imageFile);

      const result = await submitReport(formData);
      setSubmitResult({
        referenceCode: result.reference_code || result.id,
        id: result.id,
      });

      // Reset form
      reset();
      removeImage();
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to submit report. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Success state
  if (submitResult) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-[#151515] border border-[#282828] rounded-2xl p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#48C78E]/15 border border-[#48C78E]/40 flex items-center justify-center">
            <CheckCircle className="w-8 h-8 text-[#48C78E]" />
          </div>
          <h2 className="text-xl font-mono font-bold mb-2">Report Submitted Successfully</h2>
          <p className="text-sm text-[#A7A7A7] font-mono mb-6">
            Your report has been received and is being processed by the AI pipeline.
          </p>

          <div className="bg-[#0B0B0B] border border-[#282828] rounded-xl p-6 mb-6">
            <p className="text-[10px] font-mono font-bold text-[#D4FF3F] uppercase tracking-wider mb-2">
              Reference Code
            </p>
            <p className="text-2xl font-mono font-black text-white tracking-widest">
              {submitResult.referenceCode}
            </p>
            <p className="text-[11px] text-[#A7A7A7] font-mono mt-2">
              Save this code to track your report status
            </p>
          </div>

          <button
            onClick={() => setSubmitResult(null)}
            className="px-6 py-2.5 rounded-lg text-sm font-mono font-bold bg-[#FF2DA8] text-white hover:bg-[#E91E93] transition-all shadow-[0_0_15px_rgba(255,45,168,0.25)]"
          >
            SUBMIT ANOTHER REPORT
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 rounded-lg bg-[#FF2DA8]/15 flex items-center justify-center">
            <FileText className="w-4 h-4 text-[#FF2DA8]" />
          </div>
          <h2 className="text-lg font-mono font-bold">Submit Incident Report</h2>
        </div>
        <p className="text-xs text-[#A7A7A7] font-mono pl-11">
          Report a disaster, infrastructure damage, or emergency situation. Your report will be processed
          by Gemini AI for extraction and matching.
        </p>
      </div>

      {/* Error */}
      {submitError && (
        <div className="mb-4 p-3 rounded-lg bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{submitError}</span>
          <button onClick={() => setSubmitError(null)} className="ml-auto text-[#FF5C68] hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Report text */}
        <div className="bg-[#151515] border border-[#282828] rounded-xl p-5">
          <label htmlFor="report-text" className="block text-[10px] font-mono font-bold text-[#D4FF3F] uppercase tracking-wider mb-2">
            Incident Description *
          </label>
          <textarea
            id="report-text"
            {...register('original_text', {
              required: 'Report text is required.',
              minLength: { value: 10, message: 'At least 10 characters required.' },
              maxLength: { value: MAX_TEXT_LENGTH, message: `Maximum ${MAX_TEXT_LENGTH} characters.` },
            })}
            rows={6}
            className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-4 py-3 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] focus:shadow-[0_0_10px_rgba(255,45,168,0.15)] transition-all resize-none"
            placeholder="Describe the incident in detail — what happened, where, how severe..."
          />
          <div className="flex justify-between mt-1.5">
            {errors.original_text && (
              <span className="text-[10px] font-mono text-[#FF5C68]">{errors.original_text.message}</span>
            )}
            <span className={`text-[10px] font-mono ml-auto ${textValue.length > MAX_TEXT_LENGTH * 0.9 ? 'text-[#F5B942]' : 'text-[#555]'}`}>
              {textValue.length}/{MAX_TEXT_LENGTH}
            </span>
          </div>
        </div>

        {/* Two-column: Language + Location */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Language */}
          <div className="bg-[#151515] border border-[#282828] rounded-xl p-5">
            <label htmlFor="report-lang" className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-2">
              <Globe className="w-3 h-3" /> Language
            </label>
            <select
              id="report-lang"
              {...register('input_language')}
              className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-4 py-2.5 text-sm font-mono text-white focus:outline-none focus:border-[#FF2DA8] transition-all appearance-none cursor-pointer"
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>

          {/* Location */}
          <div className="bg-[#151515] border border-[#282828] rounded-xl p-5">
            <label htmlFor="report-location" className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-2">
              <MapPin className="w-3 h-3" /> Location
            </label>
            <input
              id="report-location"
              type="text"
              {...register('location_text')}
              className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-4 py-2.5 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] transition-all"
              placeholder="e.g. Andheri West, Mumbai"
            />
          </div>
        </div>

        {/* Image upload */}
        <div className="bg-[#151515] border border-[#282828] rounded-xl p-5">
          <label className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-3">
            <ImageIcon className="w-3 h-3" /> Photo Evidence <span className="text-[#555]">(optional)</span>
          </label>

          {imagePreview ? (
            <div className="relative rounded-lg overflow-hidden border border-[#282828]">
              <img
                src={imagePreview}
                alt="Upload preview"
                className="w-full h-48 object-cover"
              />
              <button
                type="button"
                onClick={removeImage}
                className="absolute top-2 right-2 p-1.5 rounded-lg bg-[#0B0B0B]/80 border border-[#282828] text-[#FF5C68] hover:bg-[#351316] transition-all"
              >
                <X className="w-4 h-4" />
              </button>
              <div className="absolute bottom-2 left-2 px-2 py-1 rounded bg-[#0B0B0B]/80 text-[10px] font-mono text-[#A7A7A7]">
                {imageFile?.name} • {((imageFile?.size || 0) / 1024 / 1024).toFixed(1)} MB
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full py-8 border-2 border-dashed border-[#282828] rounded-lg hover:border-[#FF2DA8]/50 transition-all flex flex-col items-center gap-2 group"
            >
              <Upload className="w-6 h-6 text-[#555] group-hover:text-[#FF2DA8] transition-colors" />
              <span className="text-xs font-mono text-[#555] group-hover:text-[#A7A7A7] transition-colors">
                Click to upload (JPEG, PNG, WebP — max {MAX_UPLOAD_MB}MB)
              </span>
            </button>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>

        {/* Reporter info (collapsed) */}
        <div className="bg-[#151515] border border-[#282828] rounded-xl p-5">
          <p className="text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-3">
            Reporter Information <span className="text-[#555]">(optional – auto-filled from your profile)</span>
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="reporter-name" className="block text-[10px] font-mono text-[#555] mb-1">Name</label>
              <input
                id="reporter-name"
                type="text"
                {...register('reporter_name')}
                className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-3 py-2 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] transition-all"
                placeholder="Your name"
              />
            </div>
            <div>
              <label htmlFor="reporter-contact" className="block text-[10px] font-mono text-[#555] mb-1">Contact</label>
              <input
                id="reporter-contact"
                type="text"
                {...register('reporter_contact')}
                className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-3 py-2 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] transition-all"
                placeholder="Phone or email"
              />
            </div>
          </div>
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl text-sm font-mono font-bold bg-gradient-to-r from-[#FF2DA8] to-[#E91E93] text-white hover:from-[#E91E93] hover:to-[#D01A82] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_25px_rgba(255,45,168,0.3)] hover:shadow-[0_0_35px_rgba(255,45,168,0.5)]"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          {isSubmitting ? 'SUBMITTING REPORT...' : 'SUBMIT REPORT'}
        </button>
      </form>
    </div>
  );
};
