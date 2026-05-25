import { create } from 'zustand';

interface ScanState {
  activeScanId: string | null;
  activeFileName: string | null;
  activeFileSize: number | null;
  previewUrl: string | null;
  scanStartTime: number | null;

  setActiveScan: (
    scanId: string,
    fileName: string,
    fileSize: number,
    previewUrl: string | null
  ) => void;
  clearActiveScan: () => void;
}

export const useScanStore = create<ScanState>((set) => ({
  activeScanId: null,
  activeFileName: null,
  activeFileSize: null,
  previewUrl: null,
  scanStartTime: null,

  setActiveScan: (scanId, fileName, fileSize, previewUrl) =>
    set({
      activeScanId: scanId,
      activeFileName: fileName,
      activeFileSize: fileSize,
      previewUrl,
      scanStartTime: Date.now(),
    }),

  clearActiveScan: () => {
    set((state) => {
      if (state.previewUrl) {
        URL.revokeObjectURL(state.previewUrl);
      }
      return {
        activeScanId: null,
        activeFileName: null,
        activeFileSize: null,
        previewUrl: null,
        scanStartTime: null,
      };
    });
  },
}));
