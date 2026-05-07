import { X, CheckCircle2, Info, AlertTriangle, XCircle } from 'lucide-react';
import { useDemoStore } from '../../stores';

const typeConfig = {
  success: { bg: 'bg-[var(--color-success-bg)] border-green-200', text: 'text-green-700', icon: CheckCircle2 },
  info: { bg: 'bg-primary-bg border-[var(--color-primary-border)]', text: 'text-primary-deep', icon: Info },
  warning: { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-700', icon: AlertTriangle },
  error: { bg: 'bg-[var(--color-error-bg)] border-red-200', text: 'text-red-700', icon: XCircle },
};

export function ToastContainer() {
  const { toasts, removeToast } = useDemoStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2">
      {toasts.map((toast) => {
        const config = typeConfig[toast.type];
        const Icon = config.icon;
        return (
          <div
            key={toast.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border animate-slide-in-right min-w-[280px] max-w-[400px] ${config.bg}`}
          >
            <Icon className={`w-5 h-5 ${config.text} flex-shrink-0`} />
            <p className={`text-sm flex-1 ${config.text}`}>{toast.message}</p>
            <button onClick={() => removeToast(toast.id)} className={`${config.text} hover:opacity-70`}>
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
