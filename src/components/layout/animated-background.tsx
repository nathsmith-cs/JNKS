"use client";

import { useEffect, useRef } from "react";

export function AnimatedBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let width = window.innerWidth;
    let height = window.innerHeight;

    canvas.width = width;
    canvas.height = height;

    // Floating orbs that create a premium ambient glow
    const orbs = Array.from({ length: 5 }, (_, i) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: 200 + Math.random() * 300,
      dx: (Math.random() - 0.5) * 0.3,
      dy: (Math.random() - 0.5) * 0.3,
      hue: i === 0 ? 25 : i === 1 ? 30 : i === 2 ? 15 : i === 3 ? 35 : 20,
      saturation: 80 + Math.random() * 20,
      alpha: 0.03 + Math.random() * 0.04,
    }));

    function animate() {
      ctx!.clearRect(0, 0, width, height);

      for (const orb of orbs) {
        // Move orbs slowly
        orb.x += orb.dx;
        orb.y += orb.dy;

        // Bounce off edges
        if (orb.x < -orb.radius || orb.x > width + orb.radius) orb.dx *= -1;
        if (orb.y < -orb.radius || orb.y > height + orb.radius) orb.dy *= -1;

        // Draw radial gradient orb
        const gradient = ctx!.createRadialGradient(
          orb.x,
          orb.y,
          0,
          orb.x,
          orb.y,
          orb.radius
        );
        gradient.addColorStop(
          0,
          `hsla(${orb.hue}, ${orb.saturation}%, 50%, ${orb.alpha * 1.5})`
        );
        gradient.addColorStop(
          0.5,
          `hsla(${orb.hue}, ${orb.saturation}%, 40%, ${orb.alpha * 0.8})`
        );
        gradient.addColorStop(
          1,
          `hsla(${orb.hue}, ${orb.saturation}%, 30%, 0)`
        );

        ctx!.fillStyle = gradient;
        ctx!.fillRect(
          orb.x - orb.radius,
          orb.y - orb.radius,
          orb.radius * 2,
          orb.radius * 2
        );
      }

      animationId = requestAnimationFrame(animate);
    }

    animate();

    const handleResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    };

    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0"
      aria-hidden="true"
    />
  );
}
