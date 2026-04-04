import type { Metadata } from "next";
import { Geist, Geist_Mono, Marmelad } from "next/font/google";
import { Navbar } from "@/components/layout/navbar";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { AccentColorProvider } from "@/components/accent-color-provider";
import { AnimatedBackground } from "@/components/layout/animated-background";
import { SplashScreen } from "@/components/layout/splash-screen";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

const marmelad = Marmelad({
  variable: "--font-marmelad",
  weight: "400",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "JNKS",
  description:
    "AI-powered three-point shooting form analysis. Record or upload your shot and get instant feedback.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${marmelad.variable} dark h-full antialiased font-sans`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider>
          <AccentColorProvider>
            <SplashScreen>
              <AnimatedBackground />
              <Navbar />
              <main className="relative z-10 flex-1">{children}</main>
            </SplashScreen>
          </AccentColorProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
