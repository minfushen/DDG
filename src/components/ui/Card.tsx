interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
  hover?: boolean;
}

export function Card({ children, className = '', padding = true, hover = false }: CardProps) {
  return (
    <div className={`card-surface ${padding ? 'p-4' : ''} ${hover ? 'hover:border-[var(--color-primary-border)] transition-all duration-200' : ''} ${className}`}>
      {children}
    </div>
  );
}
