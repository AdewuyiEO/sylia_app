import React, { createContext, useContext, useState, useCallback } from 'react';
import { Toast, type ToastData } from '../design/components/Toast';

/**
 * App-wide toast. Single slot: a new toast replaces the current one. Mounted
 * once in the root layout so any screen can raise one.
 */
const ToastCtx = createContext<(t: ToastData) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<ToastData | null>(null);
  const raise = useCallback((t: ToastData) => setData({ ...t }), []);
  return (
    <ToastCtx.Provider value={raise}>
      {children}
      <Toast data={data} onClear={() => setData(null)} />
    </ToastCtx.Provider>
  );
}
