interface Props {
  className?: string;
}

export function HashChainIcon({ className = "h-5 w-5" }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M9 7H6a3 3 0 0 0 0 6h3" />
      <path d="M15 7h3a3 3 0 0 1 0 6h-3" />
      <path d="M8 10h8" />
      <circle cx="20" cy="20" r="2" />
      <circle cx="4" cy="20" r="2" />
      <path d="M6 20h12" />
    </svg>
  );
}
