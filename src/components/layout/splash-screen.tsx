"use client";

// import { useState, useEffect } from "react";

// Splash screen temporarily disabled — 3D ball loading issues on mobile
// To re-enable, uncomment the original implementation below

export function SplashScreen({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

/*
// Original splash screen implementation:
export function SplashScreenOriginal({ children }: { children: React.ReactNode }) {
  const [visible, setVisible] = useState(true);
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setFadeOut(true), 2400);
    const remove = setTimeout(() => setVisible(false), 3100);
    return () => {
      clearTimeout(timer);
      clearTimeout(remove);
    };
  }, []);

  return (
    <>
      {visible && (
        <div
          className={`fixed inset-0 z-[200] flex items-center justify-center bg-black transition-opacity duration-700 ${
            fadeOut ? "opacity-0" : "opacity-100"
          }`}
        >
          <img
            src="/jnkslogo.svg"
            alt="JNKS"
            className="h-[55rem] w-auto animate-splash-logo brightness-[1.6]"
          />
        </div>
      )}
      {children}
    </>
  );
}
*/
