"use client";

import React, { useState, useEffect } from "react";

export interface CosmicParallaxBgProps {
  head?: string;
  text?: string;
  loop?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export const CosmicParallaxBg: React.FC<CosmicParallaxBgProps> = ({
  head = "LUNARALIGN",
  text = "REGISTER · MATCH · ANALYZE",
  loop = true,
  className = "",
  children,
}) => {
  // Generate sparse, delicate star-shadows once on mount (2000px coordinate space)
  const generateStars = (count: number, opacity: number = 0.85): string => {
    const stars: string[] = [];
    for (let i = 0; i < count; i++) {
      const x = Math.floor(Math.random() * 2000);
      const y = Math.floor(Math.random() * 2000);
      stars.push(`${x}px ${y}px rgba(255, 255, 255, ${opacity})`);
    }
    return stars.join(", ");
  };

  const [starLayers, setStarLayers] = useState<{ s1: string; s2: string; s3: string } | null>(null);

  useEffect(() => {
    setStarLayers({
      s1: generateStars(280, 0.75), // small 1px sparse stars
      s2: generateStars(90, 0.85),  // medium 1.5px stars
      s3: generateStars(35, 0.95),  // 2px slightly brighter stars
    });
  }, []);

  return (
    <div
      className={`relative w-full h-screen overflow-hidden bg-[#030712] text-white flex flex-col items-center justify-center select-none ${className}`}
      style={{
        background: "linear-gradient(to bottom, #02050e 0%, #060e22 35%, #0a1736 50%, #000104 52%)",
      }}
    >
      {/* Sparse Animated Parallax Star Layers (pointer-events: none, only visible above horizon) */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
        {starLayers && (
          <>
            <div
              className={`cosmic-star-layer cosmic-star-1 ${loop ? "animate-stars-slow" : ""}`}
              style={{ boxShadow: starLayers.s1 }}
            />
            <div
              className={`cosmic-star-layer cosmic-star-2 ${loop ? "animate-stars-medium" : ""}`}
              style={{ boxShadow: starLayers.s2 }}
            />
            <div
              className={`cosmic-star-layer cosmic-star-3 ${loop ? "animate-stars-fast" : ""}`}
              style={{ boxShadow: starLayers.s3 }}
            />
          </>
        )}
      </div>

      {/* Atmospheric Soft Blue Illumination (emanating upward along horizon curve) */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[85vw] max-w-6xl h-[220px] bg-blue-500/25 rounded-full blur-[75px] pointer-events-none z-1"
      />
      <div
        className="absolute top-[49%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[65vw] max-w-4xl h-[120px] bg-sky-400/20 rounded-full blur-[45px] pointer-events-none z-1"
      />

      {/* Planetary Horizon Body: Broad, Shallow Ellipse crossing the middle of the screen */}
      <div
        className="absolute left-1/2 top-[50%] -translate-x-1/2 w-[190vw] sm:w-[170vw] md:w-[155vw] lg:w-[140vw] h-[130vh] rounded-[50%] bg-[#000104] pointer-events-none z-10"
        style={{
          boxShadow:
            "0 -12px 50px rgba(37, 99, 235, 0.45), 0 -3px 18px rgba(125, 211, 252, 0.55), inset 0 2px 8px rgba(255, 255, 255, 0.15)",
        }}
      />

      {/* Center Content Stack: Title immediately above horizon, feature text below horizon */}
      <div className="relative z-20 w-full h-full flex flex-col items-center justify-center px-4 pointer-events-none">
        {/* Title: Thin, widely spaced uppercase lettering resting right on the horizon */}
        <div className="absolute top-[49%] left-1/2 -translate-x-1/2 -translate-y-[100%] w-full text-center px-4 pb-1 sm:pb-2">
          <h1
            className="text-3xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-[200] uppercase text-transparent bg-clip-text bg-gradient-to-b from-white via-slate-100 to-slate-300 tracking-[0.25em] sm:tracking-[0.35em] md:tracking-[0.42em] lg:tracking-[0.48em] transition-all duration-1000 ease-out animate-hero-fade leading-none"
            style={{
              textShadow: "0 0 25px rgba(255, 255, 255, 0.15), 0 0 40px rgba(59, 130, 246, 0.2)",
            }}
          >
            {head}
          </h1>
        </div>

        {/* Feature Text: Small, light-grey uppercase lettering centered below the horizon */}
        <div className="absolute top-[54%] left-1/2 -translate-x-1/2 w-full text-center px-4 pt-3 sm:pt-4">
          <p className="text-[10px] sm:text-xs md:text-sm font-[300] uppercase tracking-[0.25em] sm:tracking-[0.35em] md:tracking-[0.42em] text-slate-400 transition-all duration-1000 delay-300 ease-out animate-hero-fade">
            {text}
          </p>

          {/* Understated Interactive Action */}
          {children && (
            <div className="mt-6 sm:mt-8 pointer-events-auto flex items-center justify-center">
              {children}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CosmicParallaxBg;
