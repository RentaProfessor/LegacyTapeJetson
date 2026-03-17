import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./StatusBar.css";

function formatTime(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function TapeCounter({ elapsed }) {
  const count = String(Math.min(9999, elapsed)).padStart(4, "0");
  return (
    <div className="tape-counter">
      {count.split("").map((d, i) => (
        <span key={i} className="counter-digit">{d}</span>
      ))}
    </div>
  );
}

function BatteryIcon() {
  return (
    <svg width="22" height="12" viewBox="0 0 22 12" className="status-icon">
      <rect x="0" y="1" width="18" height="10" rx="2" fill="none" stroke="#888" strokeWidth="1.2" />
      <rect x="19" y="3.5" width="2.5" height="5" rx="1" fill="#888" />
      <rect x="2" y="3" width="14" height="6" rx="1" fill="#5a5" />
    </svg>
  );
}

function BluetoothIcon() {
  return (
    <svg width="10" height="14" viewBox="0 0 10 14" className="status-icon">
      <path d="M 5 0 L 5 14 M 5 0 L 9 4 L 1 10 M 5 14 L 9 10 L 1 4" fill="none" stroke="#68f" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const statusVariants = {
  initial: { opacity: 0, y: -4, scale: 0.96 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: 4, scale: 0.96 },
};

const statusTransition = { duration: 0.25, ease: "easeOut" };

function ConnectionDot({ connected }) {
  return (
    <span
      className="conn-dot"
      style={{ color: connected ? "#4a4" : "#a44" }}
      title={connected ? "Connected" : "Disconnected"}
    >
      ●
    </span>
  );
}

const APP_VERSION = "v0.4";

export default function StatusBar({ state, mode, elapsed, connected }) {
  const isRecording = state === "recording";
  const isActive = ["recording", "playback", "paused", "rewinding", "ffwd"].includes(state);

  return (
    <div className="status-bar">
      <div className="status-left">
        <AnimatePresence mode="wait">
          {isRecording ? (
            <motion.div
              key="recording"
              className="status-recording"
              variants={statusVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={statusTransition}
            >
              <motion.span
                className="rec-dot"
                animate={{ opacity: [1, 0.15, 1], scale: [1, 1.15, 1] }}
                transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
              >
                ●
              </motion.span>
              <span className="rec-text">RECORDING</span>
            </motion.div>
          ) : state === "paused" ? (
            <motion.div key="paused" className="status-paused" variants={statusVariants} initial="initial" animate="animate" exit="exit" transition={statusTransition}>
              <span className="pause-icon">❚❚</span>
              <span className="pause-text">PAUSED</span>
            </motion.div>
          ) : state === "playback" ? (
            <motion.div key="play" className="status-playing" variants={statusVariants} initial="initial" animate="animate" exit="exit" transition={statusTransition}>
              <span className="play-icon">▶</span>
              <span className="play-text">PLAYING</span>
            </motion.div>
          ) : state === "rewinding" ? (
            <motion.div key="rew" className="status-transport" variants={statusVariants} initial="initial" animate="animate" exit="exit" transition={statusTransition}>
              <span className="transport-icon">◀◀</span>
              <span className="transport-text">REWIND</span>
            </motion.div>
          ) : state === "ffwd" ? (
            <motion.div key="ff" className="status-transport" variants={statusVariants} initial="initial" animate="animate" exit="exit" transition={statusTransition}>
              <span className="transport-icon">▶▶</span>
              <span className="transport-text">FAST FWD</span>
            </motion.div>
          ) : state === "transcribing" ? (
            <motion.div key="transcribing" className="status-transcribing" variants={statusVariants} initial="initial" animate="animate" exit="exit" transition={statusTransition}>
              <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }}>
                ◉
              </motion.span>
              <span className="transcribe-text">PROCESSING</span>
            </motion.div>
          ) : (
            <motion.div key="idle" className="status-idle" variants={statusVariants} initial="initial" animate="animate" exit="exit" transition={statusTransition}>
              <span className="idle-text">READY</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="status-center">
        {isActive && <span className="timer">{formatTime(elapsed)}</span>}
      </div>

      <div className="status-right">
        <TapeCounter elapsed={elapsed} />
        <ConnectionDot connected={connected} />
        <BatteryIcon />
        <span className="version-label">{APP_VERSION}</span>
      </div>
    </div>
  );
}
