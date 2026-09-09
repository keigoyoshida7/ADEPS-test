import { asset } from './assets';
export const isLocalEngine = import.meta.env.VITE_ANALYSIS_MODE === 'local';
let worker: Worker | undefined;
let sequence = 0;
let statusPromise: Promise<Record<string, any>> | undefined;
const pending = new Map<
  number,
  { resolve: (value: any) => void; reject: (error: Error) => void }
>();
function stop(error: Error) {
  worker?.terminate();
  worker = undefined;
  statusPromise = undefined;
  for (const item of pending.values()) item.reject(error);
  pending.clear();
}
function request(
  operation: string,
  config: unknown = {},
  bytes?: ArrayBuffer,
): Promise<Record<string, any>> {
  if (!worker) {
    worker = new Worker(
      new URL(asset('/analysis-worker.mjs'), document.baseURI),
      { type: 'module' },
    );
    worker.onmessage = ({ data }) => {
      if (data.kind === 'progress') return;
      const item = pending.get(data.id);
      if (!item) return;
      pending.delete(data.id);
      if (data.kind === 'error') item.reject(new Error(data.error.message));
      else item.resolve(data.result);
    };
    worker.onerror = (e) =>
      stop(
        new Error(
          e.message ||
            '計算エンジンを読み込めませんでした。ネット接続を確認して再読み込みしてください。',
        ),
      );
    worker.onmessageerror = () =>
      stop(new Error('計算結果の受信に失敗しました。'));
  }
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker!.postMessage({ id, operation, config, bytes }, bytes ? [bytes] : []);
  });
}
export async function analysisApi(
  path: string,
  data?: unknown,
  binary?: ArrayBuffer,
): Promise<Record<string, any>> {
  if (isLocalEngine) {
    const response = await fetch(
      `/lab-api/${path}`,
      data !== undefined || binary
        ? {
            method: 'POST',
            headers: {
              'Content-Type': binary ? 'application/zip' : 'application/json',
            },
            body: binary || JSON.stringify(data),
          }
        : {},
    );
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
    return value;
  }
  if (path === 'max') throw new Error('Web版では実機を制御できません。');
  if (path === 'status')
    return (statusPromise ||= request('status').catch((error) => {
      statusPromise = undefined;
      throw error;
    }));
  return request(path, data, binary);
}
