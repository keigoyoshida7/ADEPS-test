// Browser adapter. Copy only reviewed scientific Python modules next to the worker
// in ./python/. No server.py or venue/reference files are required or loaded.
export const PYODIDE_VERSION = "314.0.6";
export const MAX_REQUEST_BYTES = 32_000_000;

const PYTHON_ADAPTER = `
import sys, json
from pathlib import Path
sys.path.insert(0, "/app/backend")
from numerics import run_demo, to_jsonable

def _adeps_report(row):
    _adeps_progress(json.dumps(row))

def _adeps_dispatch_json(operation, config_json):
    try:
        config = json.loads(config_json)
        if not isinstance(config, dict):
            raise ValueError("JSON object required")
        if operation == "playback":
            if config.get("geometry_profile", "virtual") != "virtual":
                raise ValueError("The public version supports the virtual layout only")
            allowed = {"lambda_relative", "reflection", "fault_gain_db", "fault_delay_ms",
                       "max_column_norm", "speaker_positions", "microphone_positions"}
            config = {key: value for key, value in config.items() if key in allowed}
            for key in ("speaker_positions", "microphone_positions"):
                if key in config and len(config[key]) > 64:
                    raise ValueError("At most 64 positions are supported")
            result = run_demo(**config, geometry_profile="virtual")
        elif operation == "capture":
            from capture import run_capture
            result = run_capture(config)
        elif operation == "neural":
            from neural import run_neural
            result = run_neural(config, progress=_adeps_report)
        elif operation == "diffusion-studio":
            from diffusion_studio import run_studio
            result, archive = run_studio(config, progress=_adeps_report)
            Path("/tmp/adeps-test-neural-output.zip").write_bytes(archive)
            result.update(filename="ADEPS_test_diffusion_studio.zip", mime="application/zip")
        elif operation == "spatial":
            from spatial import run_spatial
            result = run_spatial(config, progress=_adeps_report)
        elif operation in ("spatial-audio", "spatial-source"):
            from spatial import run_spatial_audio, run_spatial_source
            function = run_spatial_source if operation == "spatial-source" else run_spatial_audio
            result, archive = function(Path("/tmp/adeps-test-input.zip").read_bytes(), config, progress=_adeps_report)
            Path("/tmp/adeps-test-neural-output.zip").write_bytes(archive)
            result.update(filename="ADEPS_test_learned_FOA_comparison.zip", mime="application/zip")
        elif operation == "neural-audio":
            from neural_audio import run_audio
            result, archive = run_audio(Path("/tmp/adeps-test-input.zip").read_bytes(), config, progress=_adeps_report)
            Path("/tmp/adeps-test-neural-output.zip").write_bytes(archive)
            result.update(filename="ADEPS_test_FOA_comparison.zip", mime="application/zip")
        elif operation in ("neural-example", "spatial-example"):
            from neural_audio import example_zip
            Path("/tmp/adeps-test-example.zip").write_bytes(example_zip())
            result = {"filename": "ADEPS_test_array_audio_example.zip", "mime": "application/zip"}
        elif operation == "ir":
            from measurements import analyze_bundle
            result = analyze_bundle(Path("/tmp/adeps-test-input.zip").read_bytes())
        elif operation == "example-ir":
            from measurements import sample_zip
            Path("/tmp/adeps-test-example.zip").write_bytes(sample_zip())
            result = {"filename": "ADEPS_test_synthetic_IR_example.zip", "mime": "application/zip"}
        else:
            raise ValueError("Unsupported browser analysis operation")
        return json.dumps({"ok": True, "result": to_jsonable(result)}, ensure_ascii=False, allow_nan=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": {"name": type(exc).__name__, "message": str(exc)}}, ensure_ascii=False)
`;

export function createAnalysisEngine({ loadPyodide, loadSource, loadModel, progress = () => {} }) {
  let ready;
  let scipyReady;
  let modelReady;
  let spatialReady;
  let queue = Promise.resolve();

  async function boot() {
    progress("runtime");
    const py = await loadPyodide();
    progress("numpy");
    await py.loadPackage("numpy");
    py.FS.mkdirTree("/app/backend");
    const names = ["numerics", "capture", "measurements", "neural", "neural_audio", "spatial", "spatial_model", "diffusion_studio"];
    const sources = await Promise.all(names.map(name => loadSource(name)));
    names.forEach((name, i) => py.FS.writeFile(`/app/backend/${name}.py`, sources[i], { encoding: "utf8" }));
    py.runPython(PYTHON_ADAPTER);
    py.globals.set("_adeps_progress", json => progress(JSON.parse(json)));
    progress("ready");
    return py;
  }

  async function execute({ operation, config = {}, bytes }) {
    if (!["status", "playback", "capture", "ir", "example-ir", "neural", "neural-audio", "neural-example", "spatial", "spatial-audio", "spatial-source", "spatial-example", "diffusion-studio"].includes(operation)) {
      throw new Error("This hosted version has no Max, Dante, or audio-device connection");
    }
    const configJson = JSON.stringify(config);
    if (!configJson || new TextEncoder().encode(configJson).byteLength > MAX_REQUEST_BYTES) {
      throw new Error("JSON request limit: 32 MB");
    }
    if (["ir", "neural-audio", "spatial-audio", "spatial-source"].includes(operation) && (!(bytes instanceof ArrayBuffer) || !bytes.byteLength || bytes.byteLength > MAX_REQUEST_BYTES)) {
      throw new Error("Choose an input WAV or ZIP no larger than 32 MB");
    }
    ready ||= boot();
    const py = await ready;
    if (["capture", "ir", "example-ir", "neural", "neural-audio", "neural-example", "spatial", "spatial-audio", "spatial-source", "spatial-example", "diffusion-studio"].includes(operation)) {
      if (!scipyReady) {
        progress("scipy");
        scipyReady = py.loadPackage("scipy");
      }
      await scipyReady;
    }
    if (["neural", "neural-audio", "diffusion-studio"].includes(operation) || (operation.startsWith("spatial") && config.include_legacy)) {
      modelReady ||= (async () => {
        progress("model");
        py.FS.mkdirTree("/app/public/models");
        for (const name of ["tiny-spatial-v1.json", "tiny-spatial-v1.npz"]) {
          py.FS.writeFile(`/app/public/models/${name}`, await loadModel(name));
        }
      })().catch(error => { modelReady = undefined; throw error; });
      await modelReady;
    }
    if (["spatial", "spatial-audio", "spatial-source"].includes(operation) && config.enabled !== false) {
      spatialReady ||= (async () => {
        progress("model");
        py.FS.mkdirTree("/app/public/models");
        for (const name of ["spatial-v1.json", "spatial-v1.npz", "spatial-tuning.json"]) {
          py.FS.writeFile(`/app/public/models/${name}`, await loadModel(name));
        }
      })().catch(error => { spatialReady = undefined; throw error; });
      await spatialReady;
    }
    if (operation === "status") {
      return {
        service: "adeps-test-audio-lab-browser",
        engine: "pyodide",
        pyodide_version: py.version,
        numpy_version: py.runPython("__import__('numpy').__version__"),
        scipy_version: scipyReady ? py.runPython("__import__('scipy').__version__") : null,
        max_available: false,
        dante_available: false,
        audio_output: "user-triggered stereo preview only; no device routing",
        data_processing: "browser memory",
      };
    }
    try {
      if (["ir", "neural-audio", "spatial-audio", "spatial-source"].includes(operation)) py.FS.writeFile("/tmp/adeps-test-input.zip", new Uint8Array(bytes));
      py.globals.set("_adeps_operation", operation);
      py.globals.set("_adeps_config_json", configJson);
      progress("computing");
      // A Python str is copied to a JavaScript string. No PyProxy leaves the
      // worker, and to_jsonable keeps existing complex/null serialization.
      const envelope = JSON.parse(py.runPython("_adeps_dispatch_json(_adeps_operation, _adeps_config_json)"));
      if (!envelope.ok) {
        const error = new Error(envelope.error.message);
        error.name = envelope.error.name;
        throw error;
      }
      if (["example-ir", "neural-example", "neural-audio", "spatial-example", "spatial-audio", "spatial-source", "diffusion-studio"].includes(operation)) {
        const path = ["neural-audio", "spatial-audio", "spatial-source", "diffusion-studio"].includes(operation) ? "/tmp/adeps-test-neural-output.zip" : "/tmp/adeps-test-example.zip";
        const zip = py.FS.readFile(path).slice();
        return { ...envelope.result, bytes: zip.buffer };
      }
      return envelope.result;
    } finally {
      py.globals.delete("_adeps_operation");
      py.globals.delete("_adeps_config_json");
      for (const path of ["/tmp/adeps-test-input.zip", "/tmp/adeps-test-example.zip", "/tmp/adeps-test-neural-output.zip"]) {
        if (py.FS.analyzePath(path).exists) py.FS.unlink(path);
      }
      progress("ready");
    }
  }

  return function request(message) {
    // One Python interpreter and one temporary IR path: serialize requests.
    const result = queue.then(() => execute(message));
    queue = result.catch(() => {});
    return result;
  };
}
