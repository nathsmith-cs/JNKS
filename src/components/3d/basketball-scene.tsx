"use client";

import { Canvas } from "@react-three/fiber";
import { Basketball } from "./basketball";

export default function BasketballScene() {
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
      <pointLight position={[-5, -3, 2]} intensity={1} color="#f97316" />
      <Basketball />
    </Canvas>
  );
}
