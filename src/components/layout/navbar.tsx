"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
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
              pathname === "/analyze" ? "text-primary" : "text-muted-foreground"
            )}
          >
            Analyze
          </Link>
        </div>
      </nav>
    </header>
  );
}
