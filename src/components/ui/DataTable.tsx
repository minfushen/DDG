import type { ReactNode } from 'react';

export interface DataTableColumn<T> {
  key: string;
  header: string;
  width?: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  onRowClick?: (row: T) => void;
  selectedKey?: string;
  footer?: ReactNode;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  selectedKey,
  footer,
  className = '',
}: DataTableProps<T>) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-4 bg-slate-50 border-b border-slate-200 px-4 h-11">
        {columns.map((col) => (
          <span
            key={col.key}
            className="text-[12px] leading-4 font-medium text-slate-500 uppercase tracking-[0.05em]"
            style={col.width ? { width: col.width, flexShrink: 0 } : { flex: 1, minWidth: 0 }}
          >
            {col.header}
          </span>
        ))}
      </div>

      {/* Body */}
      <div className="flex flex-col">
        {data.map((row) => {
          const key = keyExtractor(row);
          const isSelected = selectedKey === key;

          return (
            <div
              key={key}
              className={`flex items-center gap-4 px-4 h-16 border-b border-slate-100 transition-colors duration-150 cursor-default
                ${onRowClick ? 'cursor-pointer' : ''}
                ${isSelected
                  ? 'bg-[#EFF6FF] border-l-2 border-l-[#2563EB]'
                  : 'bg-white hover:bg-slate-50'}
              `}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((col) => (
                <div
                  key={col.key}
                  style={col.width ? { width: col.width, flexShrink: 0 } : { flex: 1, minWidth: 0 }}
                >
                  {col.render(row)}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {footer && (
        <div className="bg-slate-50 border-t border-slate-200 px-4 py-3">
          {footer}
        </div>
      )}
    </div>
  );
}
