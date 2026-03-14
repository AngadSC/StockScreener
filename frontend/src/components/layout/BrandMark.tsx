import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
  size?: "sm" | "md";
}

export default function BrandMark({ className, size = "md" }: BrandMarkProps) {
  const dimensions = size === "sm" ? "h-9 w-9" : "h-11 w-11";

  return (
    <div
      className={cn(
        "relative grid place-items-center rounded-xl border border-primary/40 bg-[radial-gradient(circle_at_top,_rgba(112,112,232,0.28),_transparent_55%),linear-gradient(180deg,_rgba(91,91,214,0.16),_rgba(15,15,26,0.95))] shadow-[var(--glow-accent)]",
        dimensions,
        className
      )}
      aria-hidden="true"
    >
      <div className="absolute inset-[5px] rounded-lg border border-primary/25" />
      <div className="text-sm font-semibold text-primary">QS</div>
    </div>
  );
}
