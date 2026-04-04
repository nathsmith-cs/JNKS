"use client";

import { Canvas } from "@react-three/fiber";
import { Basketball } from "./basketball";
import { useAccentColor } from "@/components/accent-color-provider";

export default function BasketballScene() {
  const { accent } = useAccentColor();

  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 45 }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
      style={{ pointerEvents: "none" }}
    >
      <ambientLight intensity={2} />
      <directionalLight position={[5, 5, 5]} intensity={3} />
      <directionalLight position={[-3, 2, 4]} intensity={1.5} />
      <pointLight position={[-5, -3, 2]} intensity={1} color={accent.hex} />
      <Basketball />
    </Canvas>
  );
}
