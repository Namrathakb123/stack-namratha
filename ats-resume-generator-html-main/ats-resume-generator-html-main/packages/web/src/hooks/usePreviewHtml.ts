// packages/web/src/hooks/usePreviewHtml.ts
import { useEffect, useState } from "react";
import type { ResumeData } from "@ats-resume/core";
import { renderResumeHtml } from "@ats-resume/core";

let _templateHtml = "";
let _css = "";

function base(path: string) {
  const b = import.meta.env.BASE_URL ?? "/";
  return (b.endsWith("/") ? b : b + "/") + path.replace(/^\//, "");
}

async function loadText(path: string) {
  const res = await fetch(path, { cache: "no-store" });
  const text = await res.text();
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  return text;
}

async function loadAssets() {
  if (_templateHtml && _css) return;

  const tplPath = base("templates/ats.html");
  const cssPath = base("templates/style.css");

  const [tpl, css] = await Promise.all([loadText(tplPath), loadText(cssPath)]);

  // anti-fallback: se vier index.html da SPA, normalmente não tem {{NAME}}
  if (!tpl.includes("{{NAME}}") || !tpl.includes("{{SKILLS_HTML}}")) {
    throw new Error("ats.html is not the resume template");
  }

  _templateHtml = tpl;
  _css = css;
}

export function usePreviewHtml(resume: ResumeData) {
  const [html, setHtml] = useState("");

  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        await loadAssets();
        setHtml(renderResumeHtml(resume, _templateHtml, _css));
      } catch (e) {
        console.error("[usePreviewHtml] failed", e);
        setHtml("");
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [resume]);

  return html;
}
