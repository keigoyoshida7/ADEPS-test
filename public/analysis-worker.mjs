import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.6/full/pyodide.mjs";
import { createAnalysisEngine } from "./analysis-core.mjs?v=0.5.1";

const request = createAnalysisEngine({
  loadPyodide,
  async loadSource(name) {
    // Relative to this module, so /repository-name/ on GitHub Pages works.
    const response = await fetch(new URL(`./python/${name}.py`, import.meta.url), { cache: "no-cache" });
    if (!response.ok) throw new Error(`Cannot load ${name}.py (${response.status})`);
    return response.text();
  },
  async loadModel(name) {
    const response = await fetch(new URL(`./models/${name}`, import.meta.url), { cache: "no-cache" });
    if (!response.ok) throw new Error(`Cannot load model (${response.status})`);
    return new Uint8Array(await response.arrayBuffer());
  },
  progress(value) { self.postMessage({ kind: "progress", ...(typeof value === "string" ? { stage: value } : value) }); },
});

self.onmessage = async ({ data }) => {
  const { id, ...message } = data;
  try {
    const result = await request(message);
    if (result?.bytes instanceof ArrayBuffer) {
      self.postMessage({ kind: "result", id, result }, [result.bytes]);
    } else {
      self.postMessage({ kind: "result", id, result });
    }
  } catch (error) {
    self.postMessage({ kind: "error", id, error: { name: error.name, message: error.message } });
  }
};
