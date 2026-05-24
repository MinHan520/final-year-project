import { create } from 'zustand';
import { postChat, type ChatMessage } from '../api/client';

interface ChatState {
  isOpen: boolean;
  boundScanId: string | null;
  transcript: ChatMessage[];
  isSending: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
  bindScan: (scanId: string | null) => void;
  send: (message: string) => Promise<void>;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  isOpen: false,
  boundScanId: null,
  transcript: [],
  isSending: false,

  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  
  bindScan: (scanId: string | null) => set({ boundScanId: scanId }),

  reset: () => set({ transcript: [], boundScanId: null }),

  send: async (message: string) => {
    const { boundScanId, transcript } = get();
    
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      text: message,
      ts: Date.now(),
    };
    
    set({
      transcript: [...transcript, userMsg],
      isSending: true,
      isOpen: true, // Auto-open if hidden
    });

    try {
      const response = await postChat({
        scan_id: boundScanId,
        message,
        history: transcript,
      });

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: response.reply,
        ts: Date.now(),
      };

      set((state) => ({
        transcript: [...state.transcript, assistantMsg],
      }));
    } catch (err) {
      console.error('Chat failed:', err);
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: 'Sorry, I encountered an error. Please try again.',
        ts: Date.now(),
      };
      set((state) => ({
        transcript: [...state.transcript, errorMsg],
      }));
    } finally {
      set({ isSending: false });
    }
  },
}));
