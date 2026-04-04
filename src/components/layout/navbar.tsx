"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import GlassSurface from "@/components/ui/glass-surface";

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 flex justify-center px-4 pt-3">
      <GlassSurface
        width="100%"
        height={56}
        borderRadius={16}
        blur={14}
        brightness={30}
        opacity={0.85}
        backgroundOpacity={0.15}
        saturation={1.2}
        className="max-w-5xl w-full"
      >
        <nav className="flex h-full w-full items-center justify-between px-5">
          <Link href="/" className="text-2xl font-bold tracking-tight">
            <span className="text-primary">JNKS</span>
          </Link>

          <div className="flex items-center gap-6">
            <Link
              href="/"
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                pathname === "/" ? "text-primary" : "text-muted-foreground"
              )}
            >
              Home
            </Link>
            <Link
              href="/analyze"
              className={cn(
                "text-sm font-medium transition-colors hover:text-primary",
                pathname === "/analyze"
                  ? "text-primary"
                  : "text-muted-foreground"
              )}
            >
              Analyze
            </Link>
          </div>
        </nav>
      </GlassSurface>
    </header>
  );
}
