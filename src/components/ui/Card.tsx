interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
  hover?: boolean;
}

export function Card({ children, className = '', padding = true, hover = false }: CardProps) {
  return (
    <div className={`bg-white rounded-2xl border border-border-default ${padding ? 'p-6' : ''} ${hover ? 'hover:border-[#93C5FD] transition-all duration-200' : ''} ${className}`}>
      {children}
    </div>
  );
}
