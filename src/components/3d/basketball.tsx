"use client";

import { useRef, useState, useEffect } from "react";
import { useFrame, useLoader } from "@react-three/fiber";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";

export function Basketball() {
  const groupRef = useRef<THREE.Group>(null!);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);

  // Load the model (has proper UVs from the original OBJ)
  const gltf = useLoader(GLTFLoader, "/models/basketball.glb");

  // Load texture asynchronously
  useEffect(() => {
    const loader = new THREE.TextureLoader();
    loader.load("/models/Basketball_Mat_Albedo.png", (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.flipY = false; // GLTF convention
      setTexture(tex);
    });
  }, []);

  // Apply texture to the model's material once loaded
  useEffect(() => {
    if (!texture) return;
    gltf.scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        (mesh.material as THREE.MeshStandardMaterial).map = texture;
        (mesh.material as THREE.MeshStandardMaterial).roughness = 0.75;
        (mesh.material as THREE.MeshStandardMaterial).metalness = 0.05;
        (mesh.material as THREE.MeshStandardMaterial).needsUpdate = true;
      }
    });
  }, [texture, gltf]);

  useFrame(({ clock }) => {
    groupRef.current.rotation.y += 0.002;
    groupRef.current.position.y = Math.sin(clock.elapsedTime * 0.8) * 0.12;
  });

  return (
    <group ref={groupRef} scale={0.11}>
      <primitive object={gltf.scene} />
    </group>
  );
}
