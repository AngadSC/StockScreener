import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  size?: "sm" | "md";
}

export default function BrandMark({ className, size = "md" }: BrandMarkProps) {
  const dimension = size === "sm" ? 36 : 44;

  return (
    <svg
      aria-hidden="true"
      className={cn("shrink-0 drop-shadow-[0_0_16px_rgba(49,169,196,0.16)]", className)}
      height={dimension}
      viewBox="0 0 48 48"
      width={dimension}
    >
      <defs>
        <linearGradient id="qs-crest" x1="12" x2="38" y1="7" y2="42">
          <stop stopColor="#55c0d6" />
          <stop offset="0.48" stopColor="#31a9c4" />
          <stop offset="1" stopColor="#6f7885" />
        </linearGradient>
        <radialGradient id="qs-glow" cx="45%" cy="20%" r="70%">
          <stop stopColor="rgba(69,181,208,0.22)" />
          <stop offset="1" stopColor="rgba(69,181,208,0)" />
        </radialGradient>
      </defs>
      <path
        d="M24 3.75 41.25 13.7v19.9L24 43.55 6.75 33.6V13.7L24 3.75Z"
        fill="url(#qs-glow)"
        stroke="url(#qs-crest)"
        strokeWidth="1.25"
      />
      <path
        d="M24 8.65 36.95 16.1v15.8L24 39.35 11.05 31.9V16.1L24 8.65Z"
        fill="rgba(15,14,19,0.86)"
        stroke="rgba(221,228,225,0.16)"
        strokeWidth="1"
      />
      <text
        fill="#dde4e1"
        fontFamily="Spectral, Times New Roman, serif"
        fontSize="23"
        fontStyle="italic"
        fontWeight="500"
        letterSpacing="-1"
        x="16.4"
        y="30.4"
      >
        Q
      </text>
      <path d="M28.25 30.2 33.1 34" stroke="#45b5d0" strokeLinecap="round" strokeWidth="1.3" />
    </svg>
  );
}
