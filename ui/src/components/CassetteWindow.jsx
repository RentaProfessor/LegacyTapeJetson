import React, { useMemo, useId } from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./CassetteWindow.css";

const HUB_R = 22;
const MIN_TAPE_R = 30;
const MAX_TAPE_R = 72;
const LCX = 235;
const RCX = 565;
const RY = 248;

function reelRadius(tapeFraction) {
  const f = Math.max(0, Math.min(1, tapeFraction));
  return MIN_TAPE_R + f * (MAX_TAPE_R - MIN_TAPE_R);
}

function SpokeHub() {
  const teethCount = 6;
  const teeth = Array.from({ length: teethCount }, (_, i) => {
    const deg = (i * 360) / teethCount;
    const rad = (deg * Math.PI) / 180;
    const inner = HUB_R - 6;
    const outer = HUB_R - 1;
    const halfAngle = (Math.PI / teethCount) * 0.6;
    const radL = rad - halfAngle;
    const radR = rad + halfAngle;
    return `M ${Math.cos(radL) * inner} ${Math.sin(radL) * inner}
            L ${Math.cos(radL) * outer} ${Math.sin(radL) * outer}
            A ${outer} ${outer} 0 0 1 ${Math.cos(radR) * outer} ${Math.sin(radR) * outer}
            L ${Math.cos(radR) * inner} ${Math.sin(radR) * inner} Z`;
  });

  const spokes = [0, 120, 240].map((deg) => {
    const rad = (deg * Math.PI) / 180;
    return {
      x1: Math.cos(rad) * 7,
      y1: Math.sin(rad) * 7,
      x2: Math.cos(rad) * (HUB_R - 7),
      y2: Math.sin(rad) * (HUB_R - 7),
    };
  });

  return (
    <g>
      <circle cx={0} cy={0} r={HUB_R} fill="#1a1c1e" stroke="#4a4e52" strokeWidth="1.2" />
      <circle cx={0} cy={0} r={HUB_R - 2} fill="none" stroke="#333" strokeWidth="0.5" />
      {teeth.map((d, i) => (
        <path key={`t${i}`} d={d} fill="#555" stroke="#666" strokeWidth="0.3" />
      ))}
      {spokes.map((s, i) => (
        <line key={i} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} stroke="#555" strokeWidth="2.5" strokeLinecap="round" />
      ))}
      <circle cx={0} cy={0} r={8} fill="#222426" stroke="#555" strokeWidth="0.8" />
      <circle cx={0} cy={0} r={4} fill="#1a1c1e" stroke="#444" strokeWidth="0.5" />
      <circle cx={0} cy={0} r={1.5} fill="#333" />
    </g>
  );
}

function TapeWinding({ radius, side }) {
  if (radius <= HUB_R + 1) return null;
  const rings = [];
  const innerStart = HUB_R + 1.5;
  const count = Math.max(1, Math.floor((radius - innerStart) / 1.2));

  for (let i = 0; i < count; i++) {
    const r = innerStart + i * 1.2;
    const t = count > 1 ? i / (count - 1) : 0;
    const opacity = 0.3 + t * 0.5;

    const rb = Math.round(55 + t * 50);
    const gb = Math.round(25 + t * 25);
    const bb = Math.round(8 + t * 16);
    const color = `rgb(${rb},${gb},${bb})`;

    rings.push(
      <circle key={i} cx={0} cy={0} r={r} fill="none" stroke={color} strokeWidth="1" opacity={opacity} />
    );
  }

  const sheenAngle = side === "left" ? 0.5 : -0.5;
  const sheenR = innerStart + (radius - innerStart) * 0.6;
  const sx1 = Math.cos(sheenAngle) * innerStart;
  const sy1 = Math.sin(sheenAngle) * innerStart;
  const sx2 = Math.cos(sheenAngle) * sheenR;
  const sy2 = Math.sin(sheenAngle) * sheenR;

  return (
    <g>
      {rings}
      <circle cx={0} cy={0} r={radius - 0.5} fill="none" stroke="#5a3010" strokeWidth="1" opacity="0.6" />
      <line x1={sx1} y1={sy1} x2={sx2} y2={sy2} stroke="rgba(255,220,180,0.1)" strokeWidth="2" strokeLinecap="round" />
    </g>
  );
}

function Reel({ cx, cy, tapeR, spinning, duration, direction, side }) {
  const animKey = `${spinning}-${direction}-${Math.round(duration * 10)}`;

  return (
    <g transform={`translate(${cx},${cy})`}>
      <circle cx={0} cy={0} r={tapeR + 1} fill="#2a1205" opacity="0.3" />
      <circle cx={0} cy={0} r={tapeR} fill="#331a08" />
      <TapeWinding radius={tapeR} side={side} />
      <circle cx={0} cy={0} r={tapeR} fill="none" stroke="#2a1005" strokeWidth="0.8" />

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
    return { x: Math.cos(rad) * 3, y: Math.sin(rad) * 3 };
  });

  const inner = (
    <g>
      {notches.map((n, i) => (
        <circle key={i} cx={n.x} cy={n.y} r={0.7} fill="#99a" />
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

function VUMeter({ level, cx, cy }) {
  const barCount = 12;
  const barWidth = 6;
  const barGap = 2;
  const totalWidth = barCount * (barWidth + barGap) - barGap;
  const startX = cx - totalWidth / 2;

  return (
    <g>
      {Array.from({ length: barCount }, (_, i) => {
        const threshold = (i + 1) / barCount;
        const active = level >= threshold;
        let fill = "#2a3a20";
        if (active) {
          if (i < 7) fill = "#44cc44";
          else if (i < 10) fill = "#cccc33";
          else fill = "#cc3333";
        }
        return (
          <rect
            key={i}
            x={startX + i * (barWidth + barGap)}
            y={cy}
            width={barWidth}
            height={8}
            rx={1}
            fill={fill}
            opacity={active ? 0.9 : 0.3}
          />
        );
      })}
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
  transcribing: "PROCESSING...",
};

function TapePath({ leftR, rightR, headY, isActive, direction }) {
  const leftTangentY = RY + leftR;
  const rightTangentY = RY + rightR;

  const guide1X = 135;
  const guide2X = 665;

  const fullPath = `M ${LCX} ${leftTangentY} L ${guide1X} ${headY - 2} Q 400 ${headY + 8} ${guide2X} ${headY - 2} L ${RCX} ${rightTangentY}`;

  return (
    <g>
      {/* Drop shadow under the tape */}
      <path d={fullPath} fill="none" stroke="rgba(0,0,0,0.3)" strokeWidth="7" strokeLinecap="round" />

      {/* Dark underside edge */}
      <path d={fullPath} fill="none" stroke="#3a1a08" strokeWidth="5.5" strokeLinecap="round" />

      {/* Main tape body — solid brown ribbon */}
      <path d={fullPath} fill="none" stroke="#7a4420" strokeWidth="4.5" strokeLinecap="round" />

      {/* Matte coating layer */}
      <path d={fullPath} fill="none" stroke="#8a5228" strokeWidth="3.5" strokeLinecap="round" />

      {/* Top surface — slight sheen */}
      <path d={fullPath} fill="none" stroke="rgba(160,100,50,0.6)" strokeWidth="2.5" strokeLinecap="round" />

      {/* Upper highlight edge — thin bright line on top of ribbon */}
      <path d={fullPath} fill="none" stroke="rgba(200,150,90,0.3)" strokeWidth="1" strokeLinecap="round" />

      {/* Moving shimmer — light reflections traveling along the tape surface */}
      {isActive && (
        <>
          <motion.path
            d={fullPath}
            fill="none"
            stroke="rgba(220,170,100,0.35)"
            strokeWidth="2.5"
            strokeDasharray="20 80"
            strokeLinecap="round"
            initial={{ strokeDashoffset: 0 }}
            animate={{ strokeDashoffset: direction >= 0 ? -500 : 500 }}
            transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
          />
          <motion.path
            d={fullPath}
            fill="none"
            stroke="rgba(255,210,140,0.2)"
            strokeWidth="1.5"
            strokeDasharray="12 120"
            strokeLinecap="round"
            initial={{ strokeDashoffset: 40 }}
            animate={{ strokeDashoffset: direction >= 0 ? -460 : 540 }}
            transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
          />
        </>
      )}

      {/* Subtle tape flutter when running */}
      {isActive && (
        <motion.path
          d={fullPath}
          fill="none"
          stroke="rgba(140,80,30,0.15)"
          strokeWidth="4"
          animate={{ y: [0, 0.3, 0, -0.3, 0] }}
          transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
        />
      )}
    </g>
  );
}

export default function CassetteWindow({ state, chapter, mode, tapeProgress, audioLevel }) {
  const c = COLORS[mode] || COLORS.clean;
  const p = Math.max(0, Math.min(1, tapeProgress || 0));

  const leftR = reelRadius(1 - p);
  const rightR = reelRadius(p);

  const spin = useMemo(() => {
    switch (state) {
      case "recording":
      case "playback":
        return { on: true, dur: 2, dir: 1 };
      case "rewinding":
        return { on: true, dur: 0.3, dir: -1 };
      case "ffwd":
        return { on: true, dur: 0.3, dir: 1 };
      default:
        return { on: false, dur: 2, dir: 1 };
    }
  }, [state]);

  const maxR = Math.max(leftR, rightR);
  const guideY = RY + maxR + 12;
  const headY = Math.min(guideY + 5, 324);
  const isActive = ["recording", "playback", "rewinding", "ffwd"].includes(state);
  const isRecording = state === "recording";

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
            <stop offset="0%" stopColor="#3e4246" />
            <stop offset="50%" stopColor="#35393d" />
            <stop offset="100%" stopColor="#2c3034" />
          </linearGradient>
          <linearGradient id="bottomGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#5e6878" />
            <stop offset="100%" stopColor="#4e5868" />
          </linearGradient>
          <radialGradient id="windowGrad" cx="50%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#4a5868" />
            <stop offset="100%" stopColor="#3a4652" />
          </radialGradient>
          <linearGradient id="labelSheen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.15)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>

        {/* Cassette outer body */}
        <rect x="16" y="4" width="768" height="382" rx="14" fill="#1e2022" />
        <rect x="20" y="8" width="760" height="374" rx="12" fill="url(#bodyGrad)" stroke="#4a4e52" strokeWidth="0.5" />

        <g clipPath="url(#body-clip)">
          {/* Label area */}
          <rect x="48" y="20" width="704" height="142" rx="5" fill={c.label} />
          <rect x="48" y="20" width="704" height="142" rx="5" fill="url(#labelSheen)" />

          {/* Side A badge */}
          <rect x="60" y="28" width="30" height="22" rx="3" fill="rgba(0,0,0,0.08)" />
          <text x="75" y="44" fill="#333" fontSize="15" fontWeight="bold" fontFamily="'Courier New',monospace" textAnchor="middle">A</text>

          {/* State text */}
          <text x="400" y="48" fill="#222" fontSize="18" fontWeight="bold" fontFamily="'Courier New',monospace" textAnchor="middle" letterSpacing="3">
            {STATE_TEXT[state] || "LEGACY TAPE"}
          </text>

          {/* VU meter during recording */}
          {isRecording && <VUMeter level={audioLevel || 0} cx={400} cy={52} />}

          {/* Three retro stripes */}
          <rect x="48" y="64" width="704" height="32" fill={c.stripe1} />
          <rect x="48" y="96" width="704" height="32" fill={c.stripe2} />
          <rect x="48" y="128" width="704" height="34" fill={c.stripe3} />

          {/* Stripe texture lines */}
          {[68, 76, 84, 100, 108, 116, 132, 140, 148, 156].map((y) => (
            <line key={y} x1="48" y1={y} x2="752" y2={y} stroke="rgba(0,0,0,0.06)" strokeWidth="0.5" />
          ))}

          {/* Tape window */}
          <rect x="48" y="166" width="704" height="164" rx="4" fill="url(#windowGrad)" stroke="#4a5666" strokeWidth="0.6" />

          {/* Bottom body strip */}
          <rect x="20" y="330" width="760" height="60" fill="url(#bottomGrad)" />
          <rect x="20" y="330" width="760" height="1" fill="#6a7888" opacity="0.2" />

          {/* Screw holes */}
          {[200, 340, 460, 600].map((x) => (
            <g key={x}>
              <circle cx={x} cy={356} r={5} fill="#3a4048" stroke="#2e3640" strokeWidth="0.6" />
              <line x1={x - 3} y1={356} x2={x + 3} y2={356} stroke="#2e3640" strokeWidth="0.8" />
              <line x1={x} y1={353} x2={x} y2={359} stroke="#2e3640" strokeWidth="0.8" />
            </g>
          ))}
          <circle cx={400} cy={356} r={3} fill="#3a4048" stroke="#2e3640" strokeWidth="0.5" />
        </g>

        {/* Reel area clipped to tape window */}
        <g clipPath="url(#wc)">
          <Reel cx={LCX} cy={RY} tapeR={leftR} spinning={spin.on} duration={spin.dur} direction={spin.dir} side="left" />
          <Reel cx={RCX} cy={RY} tapeR={rightR} spinning={spin.on} duration={spin.dur * 0.78} direction={spin.dir} side="right" />

          <TapePath leftR={leftR} rightR={rightR} headY={headY} isActive={isActive} direction={spin.dir} />

          <GuideRoller cx={135} cy={headY - 2} spinning={isActive} direction={spin.dir} />
          <GuideRoller cx={665} cy={headY - 2} spinning={isActive} direction={spin.dir} />

          {/* Playback head */}
          <rect x={365} y={headY + 2} width={70} height={8} rx={2} fill="#778" stroke="#99a" strokeWidth="0.4" />
          <rect x={380} y={headY + 3} width={40} height={6} rx={1.5} fill="#889" opacity="0.5" />
        </g>
      </svg>
    </div>
  );
}
