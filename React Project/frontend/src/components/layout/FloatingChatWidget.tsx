import { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../../stores/chat-store';
import { MessageSquare, X, Send, Loader2 } from 'lucide-react';

export function FloatingChatWidget() {
  const { isOpen, toggle, transcript, isSending, send, boundScanId, bindScan } = useChatStore();
  const [input, setInput] = useState('');
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
        className="fixed bottom-6 right-6 p-4 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary-hover transition-transform hover:scale-105 z-50"
      >
        <MessageSquare className="size-6" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-[400px] h-[600px] max-h-[80vh] flex flex-col bg-card border border-border shadow-2xl rounded-xl overflow-hidden z-50">
      <div className="bg-gradient-to-r from-primary to-primary-hover p-4 text-primary-foreground flex justify-between items-center shrink-0">
        <div>
          <h3 className="font-medium font-display flex items-center gap-2">
            <span className="size-2 rounded-full bg-success animate-pulse" />
            Forensic Assistant
          </h3>
          {boundScanId && (
            <p className="text-xs opacity-80 mt-1 flex items-center gap-2">
              Context: {boundScanId.slice(0, 8)}...
              <button onClick={() => bindScan(null)} className="underline hover:text-white">Unbind</button>
            </p>
          )}
        </div>
        <button onClick={toggle} className="p-1 hover:bg-white/20 rounded transition-colors">
          <X className="size-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-bg">
        {transcript.length === 0 ? (
          <div className="text-center text-sm text-muted mt-10">
            Hello! I'm your TruthLens assistant. How can I help with your forensic audit today?
          </div>
        ) : (
          transcript.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-tr-sm'
                    : 'bg-card text-fg border border-border rounded-tl-sm'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))
        )}
        {isSending && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-card border border-border rounded-tl-sm">
              <Loader2 className="size-4 animate-spin text-muted" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-3 bg-card border-t border-border shrink-0">
        <form onSubmit={handleSubmit} className="relative flex items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            disabled={isSending}
            rows={1}
            className="w-full bg-bg border border-border rounded-lg pl-3 pr-10 py-3 text-sm text-fg placeholder:text-muted focus:outline-none focus:border-primary resize-none disabled:opacity-50 min-h-[44px] max-h-[120px]"
            style={{
              height: input ? 'auto' : '44px',
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isSending}
            className="absolute right-2 bottom-2 p-1.5 text-primary hover:bg-primary/10 rounded disabled:opacity-50 transition-colors"
          >
            <Send className="size-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
