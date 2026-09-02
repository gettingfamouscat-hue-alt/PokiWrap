"use client";

import { useEffect, useState } from "react";

type Platform = "windows" | "mac" | "other";

function detect(): Platform {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("mac os") || ua.includes("macintosh")) return "mac";
  if (ua.includes("windows")) return "windows";
  return "other";
}

function githubAsset(repo: string, name: string) {
  return `https://github.com/${repo}/releases/latest/download/${name}`;
}

export function DownloadButtons() {
  const repo = process.env.NEXT_PUBLIC_GITHUB_REPO || "";
  const windowsFallback = "/downloads/PokiWrap-windows.exe";
  const macFallback = "/downloads/PokiWrap-mac.zip";
  const windowsUrl = repo ? githubAsset(repo, "PokiWrap-windows.exe") : windowsFallback;
  const macUrl = repo ? githubAsset(repo, "PokiWrap-mac.zip") : macFallback;

  const [platform, setPlatform] = useState<Platform>("other");
  useEffect(() => {
    setPlatform(detect());
  }, []);

  return (
    <>
      <div className="downloads">
        <article className={`card${platform === "windows" ? " recommended" : ""}`}>
          <h2>Windows</h2>
          <p>Native .exe with Edge WebView2, taskbar icons, and desktop shortcuts.</p>
          <a className="btn" href={windowsUrl}>
            Download for Windows
          </a>
        </article>
        <article className={`card${platform === "mac" ? " recommended" : ""}`}>
          <h2>macOS</h2>
          <p>PokiWrap.app for Apple Silicon and Intel. Unzip, then double-click Open PokiWrap.</p>
          <a className={platform === "mac" ? "btn" : "btn ghost"} href={macUrl}>
            Download for Mac
          </a>
        </article>
      </div>
      <p className="hint">
        {platform === "windows"
          ? "We detected Windows — grab that installer. macOS is available too."
          : platform === "mac"
            ? "If macOS says the app is damaged, unzip the download and double-click Open PokiWrap. That clears Gatekeeper."
            : "Pick your platform. Files come from the latest GitHub release, or /downloads if you host them yourself."}
      </p>
      {platform === "mac" ? (
        <p className="hint mac-help">
          Or paste this in Terminal:
          <code>xattr -cr ~/Downloads/PokiWrap.app && open ~/Downloads/PokiWrap.app</code>
        </p>
      ) : null}
    </>
  );
}
