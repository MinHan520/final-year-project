import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../../stores/chat-store';
import { MessageSquare, X, Send, Bot, User, Loader2, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function FloatingChatWidget() {
  const { isOpen, toggle, transcript, isSending, send, boundScanId, bindScan, clearHistory } = useChatStore();
  const [input, setInput] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcript, isOpen, isSending]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;
    send(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={toggle}
        className="fixed bottom-6 right-6 p-4 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 text-white shadow-[0_0_25px_rgba(168,85,247,0.55),_0_0_50px_rgba(236,72,153,0.25)] hover:shadow-[0_0_35px_rgba(168,85,247,0.75),_0_0_70px_rgba(236,72,153,0.40)] hover:scale-105 transition-all z-50 cursor-pointer"
        aria-label="Open Chat"
      >
        <MessageSquare className="size-6" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-[400px] h-[600px] max-h-[85vh] flex flex-col bg-gradient-to-b from-purple-50/95 to-pink-50/95 dark:from-slate-900/95 dark:to-slate-950/95 backdrop-blur-xl border border-purple-500/15 rounded-2xl shadow-[0_0_40px_rgba(168,85,247,0.18),_0_0_80px_rgba(236,72,153,0.09)] overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-5 duration-200">

      {/* ── Header ───────────────────────── */}
      <div className="bg-gradient-to-r from-purple-100/80 to-pink-100/80 dark:from-purple-900/40 dark:to-pink-900/20 p-4 border-b border-purple-500/15 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-xl bg-gradient-to-br from-purple-500/25 to-pink-500/15 flex items-center justify-center shrink-0 shadow-[0_0_12px_rgba(168,85,247,0.25)]">
            <Bot className="size-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-fg">TruthLens Assistant</h3>
            {boundScanId ? (
              <p className="text-xs text-primary flex items-center gap-1 mt-0.5 text-left">
                Context: {boundScanId.slice(0, 8)}...
                <button
                  onClick={() => bindScan(null)}
                  className="text-muted-foreground hover:text-fg underline decoration-muted-foreground/30 underline-offset-2 ml-1 cursor-pointer"
                >
                  Clear
                </button>
              </p>
            ) : (
              <p className="text-xs text-muted-foreground mt-0.5 text-left">Ready to help</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={clearHistory}
            title="Clear chat history"
            className="p-2 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer"
          >
            <Trash2 className="size-4" />
          </button>
          <button
            onClick={toggle}
            className="p-2 text-muted-foreground hover:text-fg hover:bg-purple-500/10 rounded-lg transition-colors cursor-pointer"
          >
            <X className="size-5" />
          </button>
        </div>
      </div>

      {/* ── Message Feed ──────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-transparent scroll-smooth">
        {transcript.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-3 opacity-70">
            <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center shadow-[0_0_20px_rgba(168,85,247,0.25)]">
              <Bot className="size-6 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-fg">How can I assist you?</p>
              <p className="text-xs text-muted-foreground max-w-[250px]">
                Ask me about deepfake detection, forensic analysis, or the status of your scans.
              </p>
            </div>
          </div>
        ) : (
          transcript.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'w-full',
                msg.role === 'user' ? 'flex justify-end' : 'flex justify-start',
              )}
            >
              {msg.role !== 'user' ? (
                <div className="flex flex-col w-full max-w-[90%] text-left">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground tracking-wider mb-1.5 uppercase">
                    <Bot className="size-3 text-primary" />
                    <span>TruthLens Assistant</span>
                  </div>
                  <div className="pl-3 border-l-2 border-primary text-sm text-fg whitespace-pre-wrap leading-relaxed font-sans py-0.5">
                    {msg.text}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-end w-full max-w-[90%] ml-auto text-right">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground tracking-wider mb-1.5 uppercase">
                    <span>User</span>
                    <User className="size-3 text-muted-foreground" />
                  </div>
                  <div className="pr-3 border-r-2 border-pink-500/40 text-sm text-fg whitespace-pre-wrap leading-relaxed font-sans py-0.5">
                    {msg.text}
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {isSending && (
          <div className="flex w-full justify-start">
            <div className="flex flex-col w-full max-w-[90%] text-left">
              <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground tracking-wider mb-1.5 uppercase">
                <Bot className="size-3 text-primary" />
                <span>TruthLens Assistant</span>
              </div>
              <div className="pl-3 border-l-2 border-primary/50 text-sm text-muted-foreground flex items-center gap-2 font-sans py-0.5">
                <Loader2 className="size-3.5 text-primary animate-spin" />
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} className="h-2" />
      </div>

      {/* ── Input Area ──────────────────────────── */}
      <form
        onSubmit={handleSubmit}
        className={cn(
          'relative flex items-end gap-2 bg-white/50 dark:bg-black/20 border-t border-purple-500/15 p-2 transition-all shrink-0 rounded-b-2xl w-full',
          isFocused
            ? 'ring-2 ring-inset ring-purple-500/40 shadow-[inset_0_0_15px_rgba(168,85,247,0.08)]'
            : '',
        )}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Type your message..."
          disabled={isSending}
          rows={1}
          className="flex-1 bg-transparent border-none py-2 px-3 text-sm text-fg placeholder:text-muted-foreground focus:outline-none focus:ring-0 resize-none disabled:opacity-50 min-h-[40px] max-h-[120px] scrollbar-none"
          style={{ height: input ? 'auto' : '40px' }}
        />
        <button
          type="submit"
          disabled={!input.trim() || isSending}
          className="p-2 mb-1 mr-1 text-white bg-gradient-to-r from-purple-600/80 to-pink-600/80 hover:from-purple-500 hover:to-pink-500 rounded-full shadow-[0_0_10px_rgba(168,85,247,0.35)] hover:shadow-[0_0_20px_rgba(236,72,153,0.5)] disabled:opacity-40 disabled:hover:from-purple-600/80 disabled:hover:to-pink-600/80 disabled:shadow-none transition-all cursor-pointer shrink-0"
        >
          <Send className="size-4" />
        </button>
      </form>
    </div>
  );
}
