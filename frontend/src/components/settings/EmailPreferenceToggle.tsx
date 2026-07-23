'use client';

import { cn } from '@/lib/utils';

interface EmailPreferenceToggleProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
  label: string;
  id?: string;
}

/**
 * Small accessible on/off switch. No Switch primitive exists in
 * components/ui yet, so this is a minimal native-button implementation:
 * role="switch" + aria-checked keeps it screen-reader friendly, and being a
 * real <button> gives free keyboard support (Enter/Space toggle, Tab focus).
 */
export function EmailPreferenceToggle({
  checked,
  onChange,
  disabled = false,
  label,
  id,
}: EmailPreferenceToggleProps) {
  return (
    <button
      type="button"
      id={id}
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors duration-[200ms] ease-out',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
        'disabled:cursor-not-allowed disabled:opacity-40',
        checked
          ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
          : 'border-[var(--border-default)] bg-[var(--bg-surface-2)]'
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'absolute left-0.5 top-0.5 h-5 w-5 rounded-full border shadow-sm transition-transform duration-[200ms] ease-out',
          checked
            ? 'translate-x-5 border-[var(--accent)] bg-[var(--bg-base)]'
            : 'translate-x-0 border-[var(--border-default)] bg-[var(--text-tertiary)]'
        )}
      />
    </button>
  );
}
