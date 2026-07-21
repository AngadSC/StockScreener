import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ====================================
// FORMATTING UTILITIES
// ====================================

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatMarketCap(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  
  if (value >= 1e12) {
    return `$${(value / 1e12).toFixed(2)}T`;
  } else if (value >= 1e9) {
    return `$${(value / 1e9).toFixed(2)}B`;
  } else if (value >= 1e6) {
    return `$${(value / 1e6).toFixed(2)}M`;
  } else {
    return `$${value.toFixed(0)}`;
  }
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function normalizePercentValue(
  value: number | null | undefined,
  mode: 'auto' | 'ratio' | 'percent' = 'auto'
): number | null {
  if (value === null || value === undefined || isNaN(value)) return null;

  if (mode === 'ratio') return value * 100;
  if (mode === 'percent') return value;

  // Auto mode: supports both ratio storage (0.4 -> 40%) and percent storage (4 -> 4%).
  return Math.abs(value) <= 1 ? value * 100 : value;
}

export function formatPercent(
  value: number | null | undefined,
  options: { mode?: 'auto' | 'ratio' | 'percent'; withSign?: boolean } = {}
): string {
  const normalized = normalizePercentValue(value, options.mode ?? 'auto');
  if (normalized === null) return 'N/A';

  const showSign = options.withSign ?? true;
  const signPrefix = showSign && normalized >= 0 ? '+' : '';
  return `${signPrefix}${normalized.toFixed(2)}%`;
}

export function formatVolume(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  
  if (value >= 1e9) {
    return `${(value / 1e9).toFixed(2)}B`;
  } else if (value >= 1e6) {
    return `${(value / 1e6).toFixed(2)}M`;
  } else if (value >= 1e3) {
    return `${(value / 1e3).toFixed(2)}K`;
  } else {
    return value.toString();
  }
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  
  try {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return 'N/A';
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return 'N/A';
  }
}

export function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  
  try {
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return 'N/A';
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'N/A';
  }
}

// Get color class for positive/negative changes
export function getChangeColor(value: number | null | undefined): string {
  if (value === null || value === undefined || isNaN(value)) return 'text-gray-500';
  return value >= 0 ? 'text-green-600' : 'text-red-600';
}
