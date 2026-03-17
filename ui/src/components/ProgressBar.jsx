import React from "react";
import { motion } from "framer-motion";
import "./ProgressBar.css";

export default function ProgressBar({ progress }) {
  const pct = Math.max(0, Math.min(100, (progress || 0) * 100));

  return (
    <div className="progress-bar">
      <motion.div
        className="progress-fill"
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      />
    </div>
  );
}
