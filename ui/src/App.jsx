import React, { useState, useEffect, useRef, useCallback } from "react";
import CassetteWindow from "./components/CassetteWindow";
import StatusBar from "./components/StatusBar";
import ChapterBar from "./components/ChapterBar";
import ProgressBar from "./components/ProgressBar";
import "./App.css";

const MODE_LABELS = {
  clean: "CLEAN",
  ai_interview: "AI INTERVIEW",
  ghost_writer: "GHOST WRITER",
};

export default function App() {
  const [deviceState, setDeviceState] = useState("idle");
  const [transport, setTransport] = useState("idle");
  const [mode, setMode] = useState("clean");
  const [elapsed, setElapsed] = useState(0);
  const [chapter, setChapter] = useState(null);
  const [story, setStory] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [tapePos, setTapePos] = useState(0);
  const [connected, setConnected] = useState(false);
  const ws = useRef(null);
  const timerRef = useRef(null);
  const tapeTimer = useRef(null);
  const tapePosRef = useRef(0);

  const state =
    deviceState === "recording" || deviceState === "transcribing" || deviceState === "paused"
      ? deviceState
      : transport;

  // --- Send action to backend via WebSocket ---
  const sendAction = useCallback((action, extra) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ action, ...extra }));
      return true;
    }
    return false;
  }, []);

  // --- WebSocket ---
  const connect = useCallback(() => {
    try {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const sock = new WebSocket(`${proto}//${window.location.host}/ws`);
      sock.onopen = () => {
        console.log("Device connected");
        setConnected(true);
      };
      sock.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.type === "state") {
          setDeviceState(d.state);
          if (d.state === "idle") setTransport("idle");
          if (d.state === "playback") setTransport("playback");
          if (d.mode) setMode(d.mode);
          if (d.story !== undefined) setStory(d.story);
          if (d.chapter !== undefined) setChapter(d.chapter);
          if (d.transcript) setTranscript(d.transcript);
        } else if (d.type === "mode") {
          setMode(d.mode);
        } else if (d.type === "new_chapter") {
          setChapter(d.chapter);
        } else if (d.type === "playback_progress") {
          if (d.progress !== undefined) {
            tapePosRef.current = d.progress;
            setTapePos(d.progress);
          }
          if (d.position !== undefined) {
            setElapsed(Math.floor(d.position));
          }
        }
      };
      sock.onerror = () => {};
      sock.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000);
      };
      ws.current = sock;
    } catch { setConnected(false); }
  }, []);

  useEffect(() => { connect(); return () => ws.current?.close(); }, [connect]);

  // --- Elapsed timer ---
  useEffect(() => {
    clearInterval(timerRef.current);
    if (state === "recording") {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((t) => t + 1), 1000);
    } else if (state === "playback") {
      timerRef.current = setInterval(() => setElapsed((t) => t + 1), 1000);
    } else if (state === "idle") {
      setElapsed(0);
    }
    return () => clearInterval(timerRef.current);
  }, [state]);

  // --- Tape position ---
  useEffect(() => {
    clearInterval(tapeTimer.current);

    let speed = 0;
    if (state === "recording" || state === "playback") speed = 0.000027;
    else if (state === "ffwd") speed = 0.002;
    else if (state === "rewinding") speed = -0.002;

    if (speed === 0) return;

    tapeTimer.current = setInterval(() => {
      const next = tapePosRef.current + speed;

      if (next >= 0.98) {
        tapePosRef.current = 0.98;
        setTapePos(0.98);
        clearInterval(tapeTimer.current);
        setTransport("idle");
        return;
      }
      if (next <= 0.02) {
        tapePosRef.current = 0.02;
        setTapePos(0.02);
        clearInterval(tapeTimer.current);
        setTransport("idle");
        return;
      }

      tapePosRef.current = next;
      setTapePos(next);
    }, 50);

    return () => clearInterval(tapeTimer.current);
  }, [state]);

  // --- Transport button handlers ---
  // Send to backend first; fall back to local state if disconnected
  const chapterNum = useRef(1);

  const handleRecord = () => {
    if (state === "recording" || state === "transcribing") return;
    if (!sendAction("record")) {
      setDeviceState("recording");
      setChapter({ chapter_num: chapterNum.current, title: `Chapter ${chapterNum.current}` });
      chapterNum.current += 1;
    }
  };

  const handleStop = () => {
    if (state === "idle") return;
    if (!sendAction("stop")) {
      setDeviceState("idle");
    }
    setTransport("idle");
  };

  const handlePause = () => {
    if (!["recording", "paused", "playback"].includes(state)) return;
    if (!sendAction("pause")) {
      if (deviceState === "recording") setDeviceState("paused");
      else if (deviceState === "paused") setDeviceState("recording");
      else if (transport === "playback") setTransport("idle");
    }
  };

  const handlePlay = () => {
    if (deviceState === "recording" || deviceState === "transcribing") return;
    if (!sendAction("play")) {
      setTransport("playback");
    }
  };

  const handleRewind = () => {
    if (deviceState === "recording" || deviceState === "transcribing") return;
    if (tapePosRef.current <= 0.03) return;
    sendAction("rewind");
    setTransport("rewinding");
  };

  const handleFfwd = () => {
    if (deviceState === "recording" || deviceState === "transcribing") return;
    if (tapePosRef.current >= 0.97) return;
    sendAction("ffwd");
    setTransport("ffwd");
  };

  const handleMode = () => {
    sendAction("mode");
    if (!connected) {
      const modes = ["clean", "ai_interview", "ghost_writer"];
      const idx = modes.indexOf(mode);
      setMode(modes[(idx + 1) % modes.length]);
    }
  };

  const handleNewStory = () => {
    if (state !== "idle") return;
    if (!sendAction("new_story")) {
      setStory(null);
      setChapter(null);
      chapterNum.current = 1;
      tapePosRef.current = 0;
      setTapePos(0);
    }
  };

  const isRecOrTranscribing = deviceState === "recording" || deviceState === "transcribing";

  return (
    <div className="legacy-tape">
      <StatusBar state={state} mode={MODE_LABELS[mode] || mode} elapsed={elapsed} />

      <CassetteWindow state={state} chapter={chapter} mode={mode} tapeProgress={tapePos} />

      <ChapterBar chapter={chapter} state={state} />

      <ProgressBar progress={tapePos} />

      <div className="transport-bar">
        <button
          className={`transport-btn rew ${state === "rewinding" ? "active" : ""}`}
          onClick={handleRewind}
          disabled={isRecOrTranscribing}
        >
          <span className="btn-icon">&#9664;&#9664;</span>
          <span className="btn-label">REW</span>
        </button>

        <button
          className={`transport-btn stop`}
          onClick={handleStop}
          disabled={state === "idle"}
        >
          <span className="btn-icon">&#9632;</span>
          <span className="btn-label">STOP</span>
        </button>

        <button
          className={`transport-btn play ${state === "playback" ? "active" : ""}`}
          onClick={handlePlay}
          disabled={isRecOrTranscribing}
        >
          <span className="btn-icon">&#9654;</span>
          <span className="btn-label">PLAY</span>
        </button>

        <button
          className={`transport-btn rec ${state === "recording" ? "active" : ""}`}
          onClick={handleRecord}
          disabled={state === "recording" || state === "transcribing"}
        >
          <span className="btn-icon">&#9679;</span>
          <span className="btn-label">REC</span>
        </button>

        <button
          className={`transport-btn pause ${state === "paused" ? "active" : ""}`}
          onClick={handlePause}
          disabled={!["recording", "paused", "playback"].includes(state)}
        >
          <span className="btn-icon">{state === "paused" ? "&#9654;" : "&#10074;&#10074;"}</span>
          <span className="btn-label">{state === "paused" ? "RESUME" : "PAUSE"}</span>
        </button>

        <button
          className={`transport-btn ff ${state === "ffwd" ? "active" : ""}`}
          onClick={handleFfwd}
          disabled={isRecOrTranscribing}
        >
          <span className="btn-icon">&#9654;&#9654;</span>
          <span className="btn-label">FF</span>
        </button>

        <button
          className="transport-btn mode"
          onClick={handleMode}
        >
          <span className="btn-icon mode-icon">&#9881;</span>
          <span className="btn-label">{MODE_LABELS[mode] || mode}</span>
        </button>

        <button
          className="transport-btn new-story"
          onClick={handleNewStory}
          disabled={state !== "idle"}
        >
          <span className="btn-icon">&#10010;</span>
          <span className="btn-label">NEW</span>
        </button>
      </div>
    </div>
  );
}
