"use client";

import { useEffect, useRef } from "react";

/** Lightweight upward-drifting particle canvas. */
export function CosmicBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    let animationId = 0;
    let width = 0;
    let height = 0;
    let lastTimestamp = 0;
    let scrollOffset = window.scrollY;
    let targetScrollOffset = window.scrollY;

    const PARTICLE_COUNT = 60;
    const DRIFT_SPEED = 0.5;

    type Particle = {
      x: number;
      y: number;
      radius: number;
      color: string;
      alpha: number;
      speed: number;
      wobble: number;
      wobbleSpeed: number;
    };

    const particles: Particle[] = [];

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      canvas!.width = Math.floor(width * pixelRatio);
      canvas!.height = Math.floor(height * pixelRatio);
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    }

    function initParticles() {
      particles.length = 0;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push(createParticle(true));
      }
    }

    function createParticle(randomY: boolean): Particle {
      const isOrchid = Math.random() > 0.45;
      return {
        x: Math.random() * width,
        y: randomY ? Math.random() * height : height + Math.random() * 40,
        radius: 2 + Math.random() * 2,
        color: isOrchid ? "124, 77, 255" : "0, 229, 255",
        alpha: (isOrchid ? 0.15 : 0.1) * (0.55 + Math.random() * 0.45),
        speed: DRIFT_SPEED * (0.7 + Math.random() * 0.6),
        wobble: Math.random() * Math.PI * 2,
        wobbleSpeed: 0.55 + Math.random() * 0.85,
      };
    }

    function handleScroll() {
      targetScrollOffset = window.scrollY;
    }

    function draw(timestamp: number) {
      const deltaSeconds = lastTimestamp ? Math.min((timestamp - lastTimestamp) / 1000, 0.05) : 0;
      lastTimestamp = timestamp;
      scrollOffset += (targetScrollOffset - scrollOffset) * 0.08;
      const parallaxY = scrollOffset * 0.018;

      ctx!.clearRect(0, 0, width, height);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        p.y -= p.speed * deltaSeconds;
        p.wobble += p.wobbleSpeed * deltaSeconds;
        const drawX = p.x + Math.sin(p.wobble) * 8;
        const drawY = p.y - parallaxY;

        if (p.y < -10) {
          particles[i] = createParticle(false);
          continue;
        }

        const edgeFade = Math.min(
          drawY / 80,
          (height - drawY) / 80,
          drawX / 60,
          (width - drawX) / 60,
          1
        );
        const finalAlpha = p.alpha * Math.max(0, edgeFade);

        ctx!.beginPath();
        ctx!.arc(drawX, drawY, p.radius, 0, Math.PI * 2);
        ctx!.fillStyle = `rgba(${p.color}, ${finalAlpha})`;
        ctx!.fill();
      }

      animationId = requestAnimationFrame(draw);
    }

    resize();
    initParticles();
    draw(0);

    window.addEventListener("resize", resize);
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0"
      style={{ willChange: "transform" }}
    />
  );
}
