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
    <div className={`overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-card-border)] bg-white ${className}`}>
      {/* Header */}
      <div className="flex h-10 items-center gap-4 border-b border-[var(--color-border-light)] bg-[var(--color-bg-layout)] px-4">
        {columns.map((col) => (
          <span
            key={col.key}
            className="text-[12px] leading-4 font-medium uppercase tracking-[0.05em] text-[var(--color-text-secondary)]"
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
              className={`flex h-14 cursor-default items-center gap-4 border-b border-[var(--color-border-light)] px-4 transition-colors duration-150
                ${onRowClick ? 'cursor-pointer' : ''}
                ${isSelected
                  ? 'border-l-2 border-l-[var(--color-primary)] bg-[var(--color-primary-bg)]'
                  : 'bg-white hover:bg-[var(--color-bg-layout)]'}
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
        <div className="border-t border-[var(--color-border-light)] bg-[var(--color-bg-layout)] px-4 py-3">
          {footer}
        </div>
      )}
    </div>
  );
}
