export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-gray-200/70 ${className ?? ''}`}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-2xl bg-white shadow-md shadow-gray-200/50 px-5 py-4 shadow-sm space-y-3">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-20" />
      </div>
      <Skeleton className="h-8 w-24" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}

export function SkeletonTaskRow() {
  return (
    <div className="flex items-center gap-4 px-5 py-4">
      <Skeleton className="h-9 w-9 shrink-0" />
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-14" />
          <Skeleton className="h-4 w-14" />
        </div>
        <Skeleton className="h-3 w-64" />
      </div>
      <Skeleton className="h-8 w-20 shrink-0" />
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="rounded-2xl bg-white shadow-md shadow-gray-200/50 p-6 shadow-sm space-y-4">
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-[300px] w-full" />
    </div>
  );
}

export function SkeletonDetailPanel() {
  return (
    <div className="rounded-2xl bg-white shadow-md shadow-gray-200/50 p-6 shadow-sm space-y-4">
      <Skeleton className="h-5 w-28" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <div className="space-y-2 pt-2">
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-2/3" />
      </div>
    </div>
  );
}
