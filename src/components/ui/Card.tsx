interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
  hover?: boolean;
}

export function Card({ children, className = '', padding = true, hover = false }: CardProps) {
  return (
    <div className={`bg-white rounded-2xl shadow-lg shadow-gray-200/50 ${padding ? 'p-6' : ''} ${hover ? 'hover:shadow-xl hover:-translate-y-1 transition-all duration-300' : ''} ${className}`}>
      {children}
    </div>
  );
}
