import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { copyToClipboard, truncateHash } from "../lib/format";

interface Props {
  hash: string;
  truncate?: boolean;
  label?: string;
  className?: string;
}

export function HashDisplay({ hash, truncate = true, label, className = "" }: Props) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    await copyToClipboard(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {label && <span className="text-xs text-ink-muted">{label}</span>}
      <code className="mono text-xs text-ink" title={hash}>
        {truncate ? truncateHash(hash) : hash}
      </code>
      <button
        type="button"
        onClick={onCopy}
        className="inline-flex h-6 w-6 items-center justify-center rounded text-ink-subtle hover:bg-canvas hover:text-ink"
        aria-label="Copy hash"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-accent" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
    </span>
  );
}
