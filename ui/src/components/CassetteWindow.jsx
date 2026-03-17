import React, { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./CassetteWindow.css";

const HUB_R = 24;
const MAX_TAPE_R = 74;
const LCX = 235;
const RCX = 565;
const RY = 248;

function reelRadius(tapeFraction) {
  const f = Math.max(0, Math.min(1, tapeFraction));
  return Math.sqrt(HUB_R * HUB_R + f * (MAX_TAPE_R * MAX_TAPE_R - HUB_R * HUB_R));
}

function SpokeHub() {
  const spokes = [0, 120, 240].map((deg) => {
    const rad = (deg * Math.PI) / 180;
    return {
      x1: Math.cos(rad) * 6,
      y1: Math.sin(rad) * 6,
      x2: Math.cos(rad) * (HUB_R - 2),
      y2: Math.sin(rad) * (HUB_R - 2),
    };
  });

  return (
    <g>
      <circle cx={0} cy={0} r={HUB_R} fill="#1a1c1e" stroke="#444" strokeWidth="1.5" />
      <circle cx={0} cy={0} r={7} fill="#222426" stroke="#555" strokeWidth="0.8" />
      {spokes.map((s, i) => (
        <line key={i} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} stroke="#555" strokeWidth="3.5" strokeLinecap="round" />
      ))}
    </g>
  );
}

function TapeWinding({ radius }) {
  if (radius <= HUB_R + 2) return null;
  const rings = [];
  const innerStart = HUB_R + 2;
  const count = Math.floor((radius - innerStart) / 1.1);

  for (let i = 0; i < count; i++) {
    const r = innerStart + i * 1.1;
    const t = count > 1 ? i / (count - 1) : 0;
    const opacity = 0.25 + t * 0.55;

    const rb = Math.round(58 + t * 48);
    const gb = Math.round(28 + t * 24);
    const bb = Math.round(10 + t * 14);
    const color = `rgb(${rb},${gb},${bb})`;

    rings.push(
      <circle key={i} cx={0} cy={0} r={r} fill="none" stroke={color} strokeWidth="0.9" opacity={opacity} />
    );
  }

  const sheenAngle = 0.6;
  const sheenR = innerStart + (radius - innerStart) * 0.65;
  const sx1 = Math.cos(sheenAngle) * innerStart;
  const sy1 = Math.sin(sheenAngle) * innerStart;
  const sx2 = Math.cos(sheenAngle) * sheenR;
  const sy2 = Math.sin(sheenAngle) * sheenR;

  return (
    <g>
      {rings}
      <circle cx={0} cy={0} r={radius - 0.5} fill="none" stroke="#5a3010" strokeWidth="1.2" opacity="0.7" />
      <line x1={sx1} y1={sy1} x2={sx2} y2={sy2} stroke="rgba(255,220,180,0.12)" strokeWidth="2.5" strokeLinecap="round" />
    </g>
  );
}

function Reel({ cx, cy, tapeR, spinning, duration, direction }) {
  const animKey = `${spinning}-${direction}-${Math.round(duration * 10)}`;

  return (
    <g transform={`translate(${cx},${cy})`}>
      <circle cx={0} cy={0} r={tapeR + 1} fill="#2a1205" opacity="0.4" />
      <circle cx={0} cy={0} r={tapeR} fill="#3a1e08" />
      <TapeWinding radius={tapeR} />
      <circle cx={0} cy={0} r={tapeR} fill="none" stroke="#2a1005" strokeWidth="1" />

      {spinning ? (
        <motion.g
          key={animKey}
          initial={{ rotate: 0 }}
          animate={{ rotate: 360 * direction }}
          transition={{ repeat: Infinity, repeatType: "loop", duration, ease: "linear" }}
          style={{ transformOrigin: "0px 0px" }}
        >
          <SpokeHub />
        </motion.g>
      ) : (
        <SpokeHub />
      )}
    </g>
  );
}

function GuideRoller({ cx, cy, spinning, direction }) {
  const notches = [0, 90, 180, 270].map((deg) => {
    const rad = (deg * Math.PI) / 180;
    return { x: Math.cos(rad) * 3.2, y: Math.sin(rad) * 3.2 };
  });

  const inner = (
    <g>
      {notches.map((n, i) => (
        <circle key={i} cx={n.x} cy={n.y} r={0.8} fill="#99a" />
      ))}
    </g>
  );

  return (
    <g transform={`translate(${cx},${cy})`}>
      <circle cx={0} cy={0} r={5} fill="#5a6068" stroke="#7a8088" strokeWidth="0.8" />
      <circle cx={0} cy={0} r={2} fill="#48505a" />
      {spinning ? (
        <motion.g
          initial={{ rotate: 0 }}
          animate={{ rotate: 360 * direction }}
          transition={{ repeat: Infinity, repeatType: "loop", duration: 1.2, ease: "linear" }}
          style={{ transformOrigin: "0px 0px" }}
        >
          {inner}
        </motion.g>
      ) : inner}
    </g>
  );
}

const COLORS = {
  clean: {
    label: "#f0e6d4",
    stripe1: "#CC4825",
    stripe2: "#D4A044",
    stripe3: "#1A7A5E",
  },
  ai_interview: {
    label: "#dce8f4",
    stripe1: "#3868B8",
    stripe2: "#6A9AD8",
    stripe3: "#1E4488",
  },
  ghost_writer: {
    label: "#f0dcea",
    stripe1: "#9A3A80",
    stripe2: "#C470B0",
    stripe3: "#5A2050",
  },
};

const STATE_TEXT = {
  recording: "RECORDING",
  playback: "PLAYING",
  rewinding: "REWINDING",
  ffwd: "FAST FORWARD",
  paused: "PAUSED",
};

function TapePath({ leftR, rightR, headY, isActive }) {
  const leftTangentY = RY + leftR;
  const rightTangentY = RY + rightR;

  const pathLines = (
    <>
      <line x1={LCX} y1={leftTangentY} x2={120} y2={headY - 3} stroke="#7a4420" strokeWidth="2" opacity="0.65" />
      <line x1={RCX} y1={rightTangentY} x2={680} y2={headY - 3} stroke="#7a4420" strokeWidth="2" opacity="0.65" />
      <path d={`M 120 ${headY - 3} Q 400 ${headY + 10} 680 ${headY - 3}`} fill="none" stroke="#7a4420" strokeWidth="2" opacity="0.65" />
      <line x1={LCX} y1={leftTangentY} x2={120} y2={headY - 3} stroke="rgba(180,120,60,0.15)" strokeWidth="4" />
      <line x1={RCX} y1={rightTangentY} x2={680} y2={headY - 3} stroke="rgba(180,120,60,0.15)" strokeWidth="4" />
    </>
  );

  if (isActive) {
    return (
      <motion.g
        animate={{ y: [0, 0.6, 0, -0.6, 0] }}
        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
      >
        {pathLines}
      </motion.g>
    );
  }

  return <g>{pathLines}</g>;
}

export default function CassetteWindow({ state, chapter, mode, tapeProgress }) {
  const c = COLORS[mode] || COLORS.clean;
  const p = Math.max(0.02, Math.min(0.98, tapeProgress || 0.02));

  const leftR = reelRadius(1 - p);
  const rightR = reelRadius(p);

  const spin = useMemo(() => {
    switch (state) {
      case "recording":
      case "playback":
        return { on: true, dur: 2.2, dir: 1 };
      case "rewinding":
        return { on: true, dur: 0.3, dir: -1 };
      case "ffwd":
        return { on: true, dur: 0.3, dir: 1 };
      default:
        return { on: false, dur: 2.2, dir: 1 };
    }
  }, [state]);

  const maxR = Math.max(leftR, rightR);
  const guideY = RY + maxR + 14;
  const headY = Math.min(guideY + 6, 326);
  const isActive = ["recording", "playback", "rewinding", "ffwd"].includes(state);

  return (
    <div className="cassette-window">
      <svg viewBox="0 0 800 390" className="cassette-svg">
        <defs>
          <clipPath id="wc">
            <rect x="48" y="166" width="704" height="164" rx="4" />
          </clipPath>
          <clipPath id="body-clip">
            <rect x="20" y="8" width="760" height="374" rx="12" />
          </clipPath>
          <linearGradient id="bodyGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3a3e42" />
            <stop offset="100%" stopColor="#2c3034" />
          </linearGradient>
          <linearGradient id="bottomGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#5e6878" />
            <stop offset="100%" stopColor="#4e5868" />
          </linearGradient>
          <radialGradient id="windowGrad" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#475566" />
            <stop offset="100%" stopColor="#3a4652" />
          </radialGradient>
        </defs>

        {/* Cassette outer body - dark edge/bezel */}
        <rect x="16" y="4" width="768" height="382" rx="14" fill="#222628" />
        <rect x="20" y="8" width="760" height="374" rx="12" fill="url(#bodyGrad)" stroke="#4a4e52" strokeWidth="0.6" />

        {/* Everything inside body clipped to rounded corners */}
        <g clipPath="url(#body-clip)">

          {/* Label area - cream/paper */}
          <rect x="48" y="20" width="704" height="142" rx="5" fill={c.label} />

          {/* Side A badge */}
          <rect x="60" y="28" width="30" height="22" rx="3" fill="rgba(0,0,0,0.1)" />
          <text x="75" y="44" fill="#222" fontSize="16" fontWeight="bold" fontFamily="'Courier New',monospace" textAnchor="middle">A</text>

          {/* State text on label */}
          <text x="400" y="48" fill="#111" fontSize="20" fontWeight="bold" fontFamily="'Courier New',monospace" textAnchor="middle" letterSpacing="4">
            {STATE_TEXT[state] || "LEGACY TAPE"}
          </text>

          {/* Three bold retro stripes */}
          <rect x="48" y="60" width="704" height="35" fill={c.stripe1} />
          <rect x="48" y="95" width="704" height="35" fill={c.stripe2} />
          <rect x="48" y="130" width="704" height="32" fill={c.stripe3} />

          {/* Tape window - blue-gray with radial gradient for depth */}
          <rect x="48" y="166" width="704" height="164" rx="4" fill="url(#windowGrad)" stroke="#4a5666" strokeWidth="0.8" />

          {/* Bottom body strip - lighter steel-blue-gray plastic */}
          <rect x="20" y="330" width="760" height="60" fill="url(#bottomGrad)" />
          <rect x="20" y="330" width="760" height="1" fill="#6a7888" opacity="0.3" />

          {/* Screw holes in bottom body */}
          <circle cx="200" cy="356" r="5" fill="#3a4048" stroke="#2e3640" strokeWidth="0.8" />
          <circle cx="340" cy="356" r="5" fill="#3a4048" stroke="#2e3640" strokeWidth="0.8" />
          <circle cx="460" cy="356" r="5" fill="#3a4048" stroke="#2e3640" strokeWidth="0.8" />
          <circle cx="600" cy="356" r="5" fill="#3a4048" stroke="#2e3640" strokeWidth="0.8" />
          <circle cx="400" cy="356" r="3" fill="#3a4048" stroke="#2e3640" strokeWidth="0.5" />

        </g>

        {/* Reel area clipped to tape window */}
        <g clipPath="url(#wc)">
          <Reel cx={LCX} cy={RY} tapeR={leftR} spinning={spin.on} duration={spin.dur} direction={spin.dir} />
          <Reel cx={RCX} cy={RY} tapeR={rightR} spinning={spin.on} duration={spin.dur * 0.78} direction={spin.dir} />

          <TapePath leftR={leftR} rightR={rightR} headY={headY} isActive={isActive} />

          {/* Guide rollers */}
          <GuideRoller cx={120} cy={headY - 3} spinning={isActive} direction={spin.dir} />
          <GuideRoller cx={680} cy={headY - 3} spinning={isActive} direction={spin.dir} />

          {/* Playback head */}
          <rect x={355} y={headY + 2} width={90} height={10} rx={3} fill="#778" stroke="#99a" strokeWidth="0.5" />
        </g>
      </svg>
    </div>
  );
}
