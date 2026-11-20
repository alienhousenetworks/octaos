'use client';

import React from 'react';

/**
 * Deterministic, path-oriented hand-drawn SVG illustrations inspired by
 * handdraw-skill. Every stroke animates smoothly on mount and respects
 * `prefers-reduced-motion: reduce`.
 */

export function HanddrawnLoopDiagram({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 460 150"
      fill="none"
      className={`w-full h-auto select-none ${className}`}
      aria-label="OctaOS autonomous operating loop"
    >
      {/* Connecting hand-drawn flow arcs */}
      <path
        d="M84 58 C 118 32, 138 32, 166 56"
        stroke="#e5a93c"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeDasharray="160"
        className="handdraw-path"
      />
      <path
        d="M236 58 C 270 32, 290 32, 318 56"
        stroke="#2dd4bf"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeDasharray="160"
        className="handdraw-path handdraw-delay-1"
      />
      <path
        d="M380 86 C 340 128, 130 128, 56 88"
        stroke="#647182"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeDasharray="420"
        className="handdraw-path handdraw-delay-2"
      />

      {/* Node 1: Intent */}
      <rect x="16" y="42" width="72" height="44" rx="7" stroke="#e5a93c" strokeWidth="1.5" fill="#11161c" />
      <text x="52" y="68" textAnchor="middle" fill="#eceff4" fontSize="11" fontWeight="600">Intent</text>

      {/* Node 2: Intel */}
      <rect x="164" y="42" width="76" height="44" rx="7" stroke="#2dd4bf" strokeWidth="1.5" fill="#11161c" />
      <text x="202" y="68" textAnchor="middle" fill="#eceff4" fontSize="11" fontWeight="600">Research</text>

      {/* Node 3: Execute */}
      <rect x="316" y="42" width="84" height="44" rx="7" stroke="#e5a93c" strokeWidth="1.5" fill="#11161c" />
      <text x="358" y="68" textAnchor="middle" fill="#eceff4" fontSize="11" fontWeight="600">Execute</text>

      {/* Feedback label */}
      <text x="225" y="136" textAnchor="middle" fill="#8b98a8" fontSize="10" fontFamily="monospace">
        closed-loop outcome learning
      </text>
    </svg>
  );
}

export function HanddrawnEmptyCanvas({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 140 86"
      fill="none"
      className={`mx-auto mb-3 h-20 w-auto select-none ${className}`}
      aria-hidden="true"
    >
      <rect
        x="18"
        y="14"
        width="104"
        height="58"
        rx="8"
        stroke="#2d3846"
        strokeWidth="1.5"
        strokeDasharray="4 4"
        fill="#0d1116"
      />
      <path
        d="M34 46 L56 30 L78 44 L104 24"
        stroke="#e5a93c"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="120"
        className="handdraw-path"
      />
      <circle cx="56" cy="30" r="3" fill="#2dd4bf" />
      <circle cx="104" cy="24" r="3" fill="#e5a93c" />
    </svg>
  );
}

export function HanddrawnWorkflowSketch({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 260 72"
      fill="none"
      className={`h-16 w-auto select-none ${className}`}
      aria-hidden="true"
    >
      <rect x="8" y="20" width="56" height="32" rx="6" stroke="#2dd4bf" strokeWidth="1.4" fill="#11161c" />
      <text x="36" y="40" textAnchor="middle" fill="#eceff4" fontSize="10">Signal</text>
      <path d="M66 36 H98" stroke="#e5a93c" strokeWidth="1.5" strokeDasharray="40" className="handdraw-path" />
      <rect x="100" y="20" width="60" height="32" rx="6" stroke="#e5a93c" strokeWidth="1.4" fill="#11161c" />
      <text x="130" y="40" textAnchor="middle" fill="#eceff4" fontSize="10">Agent</text>
      <path d="M162 36 H194" stroke="#2dd4bf" strokeWidth="1.5" strokeDasharray="40" className="handdraw-path handdraw-delay-1" />
      <rect x="196" y="20" width="56" height="32" rx="6" stroke="#60a5fa" strokeWidth="1.4" fill="#11161c" />
      <text x="224" y="40" textAnchor="middle" fill="#eceff4" fontSize="10">Action</text>
    </svg>
  );
}
