"use client";

import React, { useState } from "react";
import RAGAssistant from "./components/RAGAssistant";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"assistant" | "metrics">("assistant");

  return (
    <div className="min-h-screen flex flex-col bg-[#f3f2f7] text-[#28243d] font-sans antialiased selection:bg-[#7052d6] selection:text-white">
      {/* Top Header */}
      <header className="w-full bg-white border-b border-[#e7e4f0] sticky top-0 z-50 transition-all">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Left: IOI Logo & Institution Info */}
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-[#7052d6] text-white flex items-center justify-center font-bold text-xs tracking-wider shadow-xs">
              IOI
            </div>
            <div className="flex flex-col">
              <span className="font-bold tracking-tight text-sm text-[#28243d] leading-tight">
                PW IOI
              </span>
              <span className="text-[11px] text-[#888099] font-medium leading-tight">
                Institute of Innovation
              </span>
            </div>
          </div>

          {/* Center: Segmented View Switcher Tabs */}
          <div className="flex items-center p-1 rounded-full bg-[#f3f0fa] border border-[#e7e4f0]">
            <button
              onClick={() => setActiveTab("assistant")}
              className={`flex items-center gap-1.5 px-3.5 sm:px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === "assistant"
                  ? "bg-white text-[#28243d] shadow-xs border border-[#e7e4f0]"
                  : "text-[#6e6785] hover:text-[#28243d]"
              }`}
            >
              <svg className="w-3.5 h-3.5 text-[#7052d6]" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L14.2 8.3L20.5 10.5L14.2 12.7L12 19L9.8 12.7L3.5 10.5L9.8 8.3L12 2Z" />
              </svg>
              <span>Assistant</span>
            </button>
            <button
              onClick={() => setActiveTab("metrics")}
              className={`flex items-center gap-1.5 px-3.5 sm:px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === "metrics"
                  ? "bg-white text-[#28243d] shadow-xs border border-[#e7e4f0]"
                  : "text-[#6e6785] hover:text-[#28243d]"
              }`}
            >
              <svg className="w-3.5 h-3.5 text-[#7052d6]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span>Observability</span>
            </button>
          </div>

          {/* Right: Demo preview Pill */}
          <div className="flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-medium border border-[#ddd6fe] bg-[#eeeafc] text-[#7052d6] shadow-2xs">
            <span className="h-2 w-2 rounded-full bg-[#7052d6] animate-pulse" />
            <span className="text-[11px] font-semibold text-[#7052d6]">Demo preview</span>
          </div>
        </div>
      </header>

      {/* Dark Purple Hero Section with Grid Pattern */}
      <section className="w-full hero-grid-bg text-white pt-12 pb-24 sm:pb-28 relative overflow-hidden">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-8 relative z-0">
          {/* Left Hero Content */}
          <div className="flex flex-col max-w-xl animate-fade-in-up">
            <div className="flex items-center gap-2 text-[#9f97bf] text-xs font-mono font-semibold tracking-widest uppercase">
              <span className="w-5 h-[1.5px] bg-[#9f97bf]" />
              <span>
                {activeTab === "assistant"
                  ? "THE KNOWLEDGE WORKSPACE / 01"
                  : "THE OBSERVABILITY WORKSPACE / 02"}
              </span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-[54px] font-extrabold tracking-tight text-white leading-[1.12] mt-4">
              A clearer answer
              <br />
              starts here.
            </h1>

            <p className="text-sm sm:text-base text-[#b5b0c7] mt-4 leading-relaxed font-normal max-w-lg">
              Explore student records with an AI assistant that shows its work. Ask a question, follow the evidence, and get straight to what matters.
            </p>
          </div>

          {/* Right Hero: Floating 3D Orbital AI Visual Graphic */}
          <div className="w-full md:w-auto flex justify-center md:justify-end select-none relative">
            {/* Background Glow */}
            <div className="w-64 h-64 rounded-full bg-[#7052d6]/25 blur-3xl absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse-glow pointer-events-none" />

            <div className="relative w-[300px] sm:w-[350px] h-[220px] flex items-center justify-center">
              <svg
                viewBox="0 0 350 220"
                className="w-full h-full"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Outer Tilted Dashed Orbit */}
                <g className="animate-orbit-spin origin-[175px_110px]">
                  <ellipse
                    cx="175"
                    cy="110"
                    rx="145"
                    ry="80"
                    stroke="rgba(190, 180, 230, 0.22)"
                    strokeWidth="1.2"
                    strokeDasharray="4 6"
                    transform="rotate(-15 175 110)"
                  />
                  {/* Satellites on outer orbit */}
                  <circle cx="295" cy="65" r="3.5" fill="#a78bfa" />
                  <circle cx="55" cy="155" r="3" fill="#a78bfa" />
                </g>

                {/* Middle Tilted Dashed Orbit */}
                <g className="animate-orbit-spin-reverse origin-[175px_110px]">
                  <ellipse
                    cx="175"
                    cy="110"
                    rx="110"
                    ry="58"
                    stroke="rgba(190, 180, 230, 0.35)"
                    strokeWidth="1.2"
                    strokeDasharray="3 5"
                    transform="rotate(-15 175 110)"
                  />
                  {/* Satellites on middle orbit */}
                  <circle cx="265" cy="120" r="3.5" fill="#c4b5fd" />
                  <circle cx="85" cy="100" r="3.5" fill="#c4b5fd" />
                </g>

                {/* Inner Orbit */}
                <ellipse
                  cx="175"
                  cy="110"
                  rx="75"
                  ry="38"
                  stroke="rgba(190, 180, 230, 0.22)"
                  strokeWidth="1"
                  strokeDasharray="2 4"
                  transform="rotate(-15 175 110)"
                />

                {/* Labels along Orbits */}
                <text
                  x="285"
                  y="40"
                  fill="#9f97bf"
                  fontSize="9"
                  fontFamily="monospace"
                  letterSpacing="0.12em"
                  fontWeight="bold"
                >
                  01 / QUERY
                </text>
                <text
                  x="30"
                  y="190"
                  fill="#9f97bf"
                  fontSize="9"
                  fontFamily="monospace"
                  letterSpacing="0.12em"
                  fontWeight="bold"
                >
                  02 / EVIDENCE
                </text>
              </svg>

              {/* Elevated Floating 3D Center Card with Sparkle */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-float-slow pointer-events-none">
                {/* Layered shadow card behind */}
                <div className="absolute -inset-1 bg-[#8c74e8]/30 rounded-[18px] rotate-3 blur-xs" />
                <div className="relative w-14 h-14 rounded-2xl bg-[#dcd4f5] shadow-lg flex items-center justify-center border border-white/60">
                  <svg className="w-6 h-6 text-[#1a1633]" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L14.4 8.6L21 11L14.4 13.4L12 20L9.6 13.4L3 11L9.6 8.6L12 2Z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Dynamic View Content */}
      <main className="flex-1 w-full pb-16">
        <RAGAssistant activeTab={activeTab} />
      </main>

      {/* Clean Footer Matching Figma Reference */}
      <footer className="w-full border-t border-[#e7e4f0] py-8 bg-[#f3f2f7] text-[#888099] text-xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>© PW Institute of Innovation</span>
          <span>Knowledge with context. Answers with confidence.</span>
        </div>
      </footer>
    </div>
  );
}
