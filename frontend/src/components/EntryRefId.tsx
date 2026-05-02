import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { copyToClipboard } from "../lib/format";

interface Props {
  refId: string;
  copyable?: boolean;
  className?: string;
}

export function EntryRefId({ refId, copyable = false, className = "" }: Props) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    await copyToClipboard(refId);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (!copyable) {
    return <span className={`mono text-sm font-medium text-primary ${className}`}>{refId}</span>;
  }

  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <span className="mono text-sm font-medium text-primary">{refId}</span>
      <button
        type="button"
        onClick={onCopy}
        className="inline-flex h-6 w-6 items-center justify-center rounded text-ink-subtle hover:bg-canvas hover:text-ink"
        aria-label="Copy entry reference"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-accent" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
    </span>
  );
}
