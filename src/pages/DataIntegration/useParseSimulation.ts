import { useState, useEffect } from 'react';
import { mockParseProgress } from '../../services/mockData';
import type { ParseItem } from './types';

/** 演示：模拟文件逐一解析完成（纯前端模拟） */
export function useParseSimulation() {
  const [parseItems, setParseItems] = useState<ParseItem[]>(() =>
    mockParseProgress.map((p) => ({ ...p, progress: 0, status: 'pending' })),
  );
  const [allDone, setAllDone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const files = mockParseProgress;

    (async () => {
      for (let i = 0; i < files.length; i++) {
        if (cancelled) return;
        const file = files[i];
        setParseItems((prev) =>
          prev.map((p, idx) => (idx === i ? { ...p, status: 'processing', progress: 0 } : p)),
        );

        await new Promise<void>((resolve) => {
          let progress = 0;
          const interval = setInterval(() => {
            progress += Math.random() * 18 + 5;
            if (progress >= 100) {
              progress = 100;
              clearInterval(interval);
              resolve();
            }
            setParseItems((prev) =>
              prev.map((p, idx) =>
                idx === i ? { ...p, progress: Math.min(100, Math.round(progress)) } : p,
              ),
            );
          }, 300);
        });

        if (cancelled) return;
        setParseItems((prev) =>
          prev.map((p, idx) =>
            idx === i ? { ...p, status: 'completed', progress: 100, result: file.result } : p,
          ),
        );
      }
      if (!cancelled) setAllDone(true);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const processingItem = parseItems.find((p) => p.status === 'processing');
  const completedCount = parseItems.filter((p) => p.status === 'completed').length;

  return {
    parseItems,
    allDone,
    processingItem,
    completedCount,
    totalCount: parseItems.length,
  };
}
