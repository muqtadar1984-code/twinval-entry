import type { Severity } from "../types/api";

const styles: Record<Severity, string> = {
  Normal: "bg-accent-50 text-accent-700 border border-accent/30",
  Watch: "bg-warning-50 text-warning-700 border border-warning/30",
  Alert: "bg-danger-50 text-danger-700 border border-danger/30",
};

const dotColors: Record<Severity, string> = {
  Normal: "bg-accent",
  Watch: "bg-warning",
  Alert: "bg-danger",
};

interface Props {
  severity: Severity;
  className?: string;
}

export function SeverityBadge({ severity, className = "" }: Props) {
  return (
    <span className={`pill ${styles[severity]} ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotColors[severity]}`} />
      {severity}
    </span>
  );
}
