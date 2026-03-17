import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./ChapterBar.css";

export default function ChapterBar({ chapter, state }) {
  let chapterText = "LEGACY TAPE";
  if (chapter && typeof chapter === "object" && chapter.chapter_num != null) {
    const title = (typeof chapter.title === "string" && chapter.title) ? chapter.title.toUpperCase() : "UNTITLED";
    chapterText = `CH ${chapter.chapter_num}: ${title}`;
  }

  const isTranscribing = state === "transcribing";

  return (
    <div className="chapter-bar">
      <AnimatePresence mode="wait">
        {isTranscribing ? (
          <motion.div
            key="transcribing"
            className="chapter-transcribing"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
          >
            <motion.span
              className="transcribe-spinner"
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
            >
              ◐
            </motion.span>
            <span>TRANSCRIBING RECORDING...</span>
          </motion.div>
        ) : (
          <motion.div
            key={chapterText}
            className="chapter-text"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
          >
            {chapterText}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
