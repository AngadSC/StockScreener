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
        "relative grid place-items-center rotate-45 border border-primary/70 bg-gradient-to-br from-primary/30 via-transparent to-secondary/30 shadow-[0_0_22px_rgba(212,175,55,0.18)]",
        dimensions,
        className
      )}
      aria-hidden="true"
    >
      <div className="absolute inset-[5px] border border-primary/40" />
      <div className="-rotate-45 font-display text-sm uppercase tracking-[0.34em] text-primary">
        QS
      </div>
    </div>
  );
}
