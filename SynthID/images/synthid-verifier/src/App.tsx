/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { 
  Upload, 
  ShieldCheck, 
  ShieldAlert, 
  Loader2, 
  FileVideo, 
  ImageIcon, 
  Info,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Scan,
  History,
  Trash2,
  Clock
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
// Using Python backend instead of direct Gemini API calls

interface DetectionResult {
  id?: string;
  timestamp?: string;
  fileName?: string;
  isAI: boolean;
  confidence: number;
  reasoning: string;
  type: 'image' | 'video';
  metadata?: {
    synthIdDetected: boolean;
    watermarkFound: boolean;
  };
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<DetectionResult[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch history on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/history');
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  const saveToHistory = async (scanResult: DetectionResult) => {
    try {
      const response = await fetch('/api/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...scanResult,
          fileName: file?.name
        })
      });
      if (response.ok) {
        fetchHistory();
      }
    } catch (err) {
      console.error('Failed to save history:', err);
    }
  };

  const clearHistory = async () => {
    try {
      const response = await fetch('/api/history', { method: 'DELETE' });
      if (response.ok) {
        setHistory([]);
      }
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      processFile(selectedFile);
    }
  };

  const processFile = (selectedFile: File) => {
    if (!selectedFile.type.startsWith('image/') && !selectedFile.type.startsWith('video/')) {
      setError('Please upload an image or video file.');
      return;
    }
    setFile(selectedFile);
    setError(null);
    setResult(null);
    setShowHistory(false);
    
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result as string);
    };
    reader.readAsDataURL(selectedFile);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      processFile(droppedFile);
    }
  };

  const analyzeContent = async () => {
    if (!file || !previewUrl) return;

    // Limit file size to 20MB for browser-based base64 processing
    if (file.size > 20 * 1024 * 1024) {
      setError('File is too large. Please upload a file smaller than 20MB for analysis.');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      console.log('Starting analysis for:', file.name, 'Type:', file.type);
      const base64Data = previewUrl.split(',')[1];
      const mimeType = file.type;

      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base64Data, mimeType, fileName: file.name, size: file.size })
      });
      
      if (!res.ok) {
        throw new Error('Analysis failed server-side');
      }
      
      const response = await res.json();

      console.log('Analysis complete. Parsing response...');
      setResult(response as DetectionResult);
      saveToHistory(response as DetectionResult);
    } catch (err) {
      console.error('Analysis error:', err);
      if (err instanceof Error && err.message.includes('413')) {
        setError('The file is too large for the API to process. Please try a smaller file.');
      } else {
        setError('Failed to analyze content. This might be due to network latency or file size. Please try again with a smaller file.');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#f5f5f5] text-[#1a1a1a] selection:bg-emerald-100">
      {/* Header */}
      <header className="border-b border-black/5 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={reset}>
            <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
              <ShieldCheck className="text-white w-5 h-5" />
            </div>
            <span className="font-semibold tracking-tight text-lg">SynthID Verifier</span>
          </div>
          <nav className="flex items-center gap-4 md:gap-6 text-sm font-medium text-gray-500">
            <button 
              onClick={() => setShowHistory(!showHistory)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${showHistory ? 'bg-emerald-100 text-emerald-700' : 'hover:bg-gray-100'}`}
            >
              <History className="w-4 h-4" />
              <span className="hidden sm:inline">History</span>
            </button>
            <a href="#" className="hidden md:inline hover:text-emerald-600 transition-colors">Technology</a>
            <a href="#" className="px-4 py-2 bg-black text-white rounded-full hover:bg-gray-800 transition-all">
              Docs
            </a>
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-12">
        <AnimatePresence mode="wait">
          {showHistory ? (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-8"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-light tracking-tight">Scan <span className="text-emerald-600 font-medium">History</span></h1>
                  <p className="text-sm text-gray-400 mt-1">Your recent verification results</p>
                </div>
                {history.length > 0 && (
                  <button 
                    onClick={clearHistory}
                    className="flex items-center gap-2 text-sm text-red-500 hover:text-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Clear All
                  </button>
                )}
              </div>

              {history.length === 0 ? (
                <div className="bg-white rounded-3xl p-20 border border-black/5 text-center space-y-4">
                  <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto">
                    <History className="w-8 h-8 text-gray-300" />
                  </div>
                  <p className="text-gray-400">No scans found in your history.</p>
                  <button 
                    onClick={() => setShowHistory(false)}
                    className="text-emerald-600 font-medium hover:underline"
                  >
                    Start your first scan
                  </button>
                </div>
              ) : (
                <div className="grid gap-4">
                  {history.map((item) => (
                    <div key={item.id} className="bg-white rounded-2xl p-6 border border-black/5 flex items-center justify-between group hover:shadow-md transition-all">
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${item.isAI ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                          {item.isAI ? <ShieldAlert className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
                        </div>
                        <div>
                          <p className="font-medium text-sm truncate max-w-[200px]">{item.fileName}</p>
                          <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                            <Clock className="w-3 h-3" />
                            {new Date(item.timestamp!).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-bold ${item.isAI ? 'text-red-600' : 'text-emerald-600'}`}>
                          {item.isAI ? 'AI Generated' : 'Authentic'}
                        </p>
                        <p className="text-xs text-gray-400">{(item.confidence * 100).toFixed(0)}% Confidence</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="main"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid lg:grid-cols-12 gap-12"
            >
              {/* Left Column: Upload & Preview */}
              <div className="lg:col-span-7 space-y-8">
                <section>
                  <h1 className="text-4xl font-light tracking-tight mb-4">
                    Verify AI Content <span className="text-emerald-600 font-medium">Authenticity</span>
                  </h1>
                  <p className="text-gray-500 max-w-md leading-relaxed">
                    Upload images or videos to detect invisible watermarks and AI-generated artifacts using advanced SynthID-inspired analysis.
                  </p>
                </section>

                {!file ? (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    onDragOver={onDragOver}
                    onDrop={onDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="group relative border-2 border-dashed border-gray-200 rounded-3xl p-12 bg-white hover:border-emerald-500/50 hover:bg-emerald-50/30 transition-all cursor-pointer overflow-hidden"
                  >
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      onChange={handleFileChange} 
                      className="hidden" 
                      accept="image/*,video/*"
                    />
                    <div className="flex flex-col items-center text-center space-y-4">
                      <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center group-hover:scale-110 group-hover:bg-emerald-100 transition-all duration-500">
                        <Upload className="w-8 h-8 text-gray-400 group-hover:text-emerald-600" />
                      </div>
                      <div>
                        <p className="text-lg font-medium">Drop your file here</p>
                        <p className="text-sm text-gray-400">Supports JPG, PNG, MP4 up to 50MB</p>
                      </div>
                    </div>
                    {/* Decorative dots */}
                    <div className="absolute top-4 right-4 flex gap-1">
                      {[1, 2, 3].map(i => <div key={i} className="w-1 h-1 rounded-full bg-gray-200" />)}
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-white rounded-3xl p-4 shadow-sm border border-black/5"
                  >
                    <div className="relative aspect-video rounded-2xl overflow-hidden bg-gray-100 group">
                      {file.type.startsWith('image') ? (
                        <img 
                          src={previewUrl!} 
                          alt="Preview" 
                          className="w-full h-full object-contain"
                          referrerPolicy="no-referrer"
                        />
                      ) : (
                        <video 
                          src={previewUrl!} 
                          className="w-full h-full object-contain"
                          controls
                        />
                      )}
                      <button 
                        onClick={reset}
                        className="absolute top-4 right-4 p-2 bg-black/50 backdrop-blur-md text-white rounded-full hover:bg-black transition-colors opacity-0 group-hover:opacity-100"
                      >
                        <AlertCircle className="w-5 h-5 rotate-45" />
                      </button>
                    </div>
                    
                    <div className="mt-6 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          {file.type.startsWith('image') ? <ImageIcon className="w-5 h-5" /> : <FileVideo className="w-5 h-5" />}
                        </div>
                        <div>
                          <p className="text-sm font-medium truncate max-w-[200px]">{file.name}</p>
                          <p className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                      </div>
                      
                      {!result && !isAnalyzing && (
                        <button
                          onClick={analyzeContent}
                          className="px-6 py-2.5 bg-emerald-600 text-white rounded-xl font-medium hover:bg-emerald-700 transition-all shadow-lg shadow-emerald-600/20 flex items-center gap-2"
                        >
                          <Scan className="w-4 h-4" />
                          Run Verification
                        </button>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* Info Section */}
                <div className="bg-white rounded-3xl p-8 border border-black/5 space-y-6">
                  <div className="flex items-center gap-2 text-emerald-600">
                    <Info className="w-5 h-5" />
                    <h3 className="font-semibold">About SynthID Technology</h3>
                  </div>
                  <p className="text-sm text-gray-500 leading-relaxed">
                    SynthID is a tool for watermarking and identifying AI-generated images. It embeds a digital watermark directly into the pixels of an image, making it imperceptible to the human eye, but detectable for identification.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 rounded-2xl border border-black/5">
                      <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Robustness</p>
                      <p className="text-sm">Resistant to crops, resizing, and compression.</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-2xl border border-black/5">
                      <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Imperceptible</p>
                      <p className="text-sm">Maintains original visual quality perfectly.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Results */}
              <div className="lg:col-span-5">
                <AnimatePresence mode="wait">
                  {isAnalyzing ? (
                    <motion.div
                      key="analyzing"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="bg-white rounded-3xl p-12 border border-black/5 flex flex-col items-center text-center space-y-6"
                    >
                      <div className="relative">
                        <div className="w-24 h-24 border-4 border-emerald-100 rounded-full" />
                        <motion.div 
                          animate={{ rotate: 360 }}
                          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                          className="absolute inset-0 w-24 h-24 border-4 border-t-emerald-600 rounded-full"
                        />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
                        </div>
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold">Analyzing Content</h3>
                        <p className="text-sm text-gray-400 mt-2">Scanning for digital watermarks and AI artifacts...</p>
                      </div>
                      <div className="w-full bg-gray-100 h-1 rounded-full overflow-hidden">
                        <motion.div 
                          initial={{ width: "0%" }}
                          animate={{ width: "100%" }}
                          transition={{ duration: 3 }}
                          className="h-full bg-emerald-600"
                        />
                      </div>
                    </motion.div>
                  ) : result ? (
                    <motion.div
                      key="result"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="space-y-6"
                    >
                      <div className={`rounded-3xl p-8 border ${result.isAI ? 'bg-red-50 border-red-100' : 'bg-emerald-50 border-emerald-100'}`}>
                        <div className="flex items-center justify-between mb-6">
                          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${result.isAI ? 'bg-red-600' : 'bg-emerald-600'}`}>
                            {result.isAI ? <ShieldAlert className="text-white w-6 h-6" /> : <ShieldCheck className="text-white w-6 h-6" />}
                          </div>
                          <div className="text-right">
                            <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Confidence</p>
                            <p className={`text-2xl font-mono font-bold ${result.isAI ? 'text-red-600' : 'text-emerald-600'}`}>
                              {(result.confidence * 100).toFixed(1)}%
                            </p>
                          </div>
                        </div>
                        
                        <h2 className="text-2xl font-bold mb-2">
                          {result.isAI ? 'AI-Generated Content' : 'Authentic Content'}
                        </h2>
                        <p className="text-sm text-gray-600 leading-relaxed">
                          {result.reasoning}
                        </p>
                      </div>

                      <div className="bg-white rounded-3xl p-8 border border-black/5 space-y-6">
                        <h3 className="font-semibold flex items-center gap-2">
                          <Scan className="w-4 h-4 text-gray-400" />
                          Technical Breakdown
                        </h3>
                        
                        <div className="space-y-4">
                          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl">
                            <span className="text-sm text-gray-500">SynthID Watermark</span>
                            {result.metadata?.synthIdDetected ? (
                              <span className="flex items-center gap-1 text-xs font-bold text-red-600 bg-red-100 px-2 py-1 rounded-full">
                                <CheckCircle2 className="w-3 h-3" /> DETECTED
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-xs font-bold text-gray-400 bg-gray-200 px-2 py-1 rounded-full">
                                NOT FOUND
                              </span>
                            )}
                          </div>
                          
                          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl">
                            <span className="text-sm text-gray-500">Visual Artifacts</span>
                            {result.isAI ? (
                              <span className="flex items-center gap-1 text-xs font-bold text-red-600 bg-red-100 px-2 py-1 rounded-full">
                                <AlertCircle className="w-3 h-3" /> PRESENT
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-xs font-bold text-emerald-600 bg-emerald-100 px-2 py-1 rounded-full">
                                <CheckCircle2 className="w-3 h-3" /> CLEAN
                              </span>
                            )}
                          </div>
                        </div>

                        <button 
                          onClick={reset}
                          className="w-full py-3 border border-gray-200 rounded-2xl text-sm font-medium hover:bg-gray-50 transition-colors"
                        >
                          Verify Another File
                        </button>
                      </div>
                    </motion.div>
                  ) : error ? (
                    <motion.div
                      key="error"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="bg-red-50 rounded-3xl p-8 border border-red-100 text-center space-y-4"
                    >
                      <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto">
                        <AlertCircle className="text-red-600 w-6 h-6" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-red-900">Analysis Failed</h3>
                        <p className="text-sm text-red-700 mt-1">{error}</p>
                      </div>
                      <button 
                        onClick={reset}
                        className="px-6 py-2 bg-white border border-red-200 rounded-xl text-sm font-medium text-red-600 hover:bg-red-100 transition-colors"
                      >
                        Try Again
                      </button>
                    </motion.div>
                  ) : (
                    <div className="bg-white rounded-3xl p-12 border border-black/5 flex flex-col items-center text-center space-y-6 opacity-50 grayscale">
                      <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center">
                        <ShieldCheck className="w-10 h-10 text-gray-300" />
                      </div>
                      <div>
                        <h3 className="text-lg font-medium">Ready for Scan</h3>
                        <p className="text-sm text-gray-400 mt-2">Upload a file to begin the verification process.</p>
                      </div>
                    </div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="border-t border-black/5 py-12 bg-white">
        <div className="max-w-5xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="flex items-center gap-2 opacity-50">
            <ShieldCheck className="w-5 h-5" />
            <span className="font-semibold tracking-tight">SynthID Verifier</span>
          </div>
          <div className="flex gap-8 text-sm text-gray-400">
            <a href="#" className="hover:text-black transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-black transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-black transition-colors">API Access</a>
          </div>
          <p className="text-sm text-gray-400">© 2026 SynthID Verification Labs</p>
        </div>
      </footer>
    </div>
  );
}
