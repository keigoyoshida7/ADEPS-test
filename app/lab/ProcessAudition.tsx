'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { auditionClipAt, buildAuditionTimeline } from './processAuditionTimeline';
import './ProcessAudition.css';

export type ProcessAuditionProps = {
  stages: { id: string; step: number; stage: string; sigma: number; preview_wav_base64: string }[];
  runKey: string;
  gain: number;
  language: 'jp' | 'en';
  active: boolean;
  onStage: (index: number) => void;
  onStart?: () => void;
  stopToken?: number;
};
type Session = { context: AudioContext; sources: AudioBufferSourceNode[]; gains: GainNode[]; frame: number };
type Position = { stage: number; repeat: number; elapsed: number; duration: number };
const sigmaText = (value: number) => value === 0 ? '0' : Number(value.toPrecision(4)).toString();

export function ProcessAudition({ stages, runKey, gain, language, active, onStage, onStart, stopToken }: ProcessAuditionProps) {
  const jp = language === 'jp';
  const [repeats, setRepeats] = useState(2);
  const [phase, setPhase] = useState<'idle' | 'loading' | 'playing'>('idle');
  const [position, setPosition] = useState<Position | null>(null);
  const [error, setError] = useState('');
  const session = useRef<Session | null>(null), generation = useRef(0);
  const callbacks = useRef({ onStage, onStart });
  useEffect(() => { callbacks.current = { onStage, onStart }; }, [onStage, onStart]);

  const stop = useCallback((updateUi = true) => {
    generation.current++;
    const current = session.current;
    session.current = null;
    if (current) {
      cancelAnimationFrame(current.frame);
      current.sources.forEach(source => { try { source.stop(); } catch { /* Already ended. */ } source.disconnect(); });
      current.gains.forEach(node => node.disconnect());
      void current.context.close().catch(() => {});
    }
    if (updateUi) { setPhase('idle'); setPosition(null); }
  }, []);

  useEffect(() => {
    // Input lifecycle changes cancel browser audio, including pending decoding.
    // oxlint-disable-next-line react/react-compiler
    stop();
  }, [active, runKey, stopToken, gain, stop]);
  useEffect(() => () => stop(false), [stop]);

  const play = async () => {
    if (!active || !stages.length || !Number.isFinite(gain) || gain < 0 || gain > 1) return;
    stop(); setError(''); setPhase('loading');
    const ticket = generation.current;
    try {
      // Construction/resume happens only inside the user's playback gesture.
      const context = new AudioContext();
      const current: Session = { context, sources: [], gains: [], frame: 0 };
      session.current = current;
      callbacks.current.onStart?.();
      await context.resume();
      const buffers = await Promise.all(stages.map(stage => {
        const bytes = Uint8Array.from(atob(stage.preview_wav_base64), char => char.charCodeAt(0));
        return context.decodeAudioData(bytes.buffer);
      }));
      if (generation.current !== ticket || session.current !== current) return;
      if (buffers.some(buffer => buffer.numberOfChannels !== 2 || buffer.duration <= 0)) throw new Error('Expected stereo WAV previews');
      const timeline = buildAuditionTimeline(buffers.map(buffer => buffer.duration), repeats);
      const master = context.createGain();
      master.gain.value = gain; master.connect(context.destination); current.gains.push(master);
      const begins = context.currentTime + .06;
      timeline.clips.forEach(clip => {
        const source = context.createBufferSource(), envelope = context.createGain();
        source.buffer = buffers[clip.stageIndex]; source.connect(envelope); envelope.connect(master);
        const start = begins + clip.start, end = begins + clip.end;
        envelope.gain.setValueAtTime(0, start);
        envelope.gain.linearRampToValueAtTime(1, start + clip.fade);
        envelope.gain.setValueAtTime(1, end - clip.fade);
        envelope.gain.linearRampToValueAtTime(0, end);
        source.start(start); source.stop(end);
        current.sources.push(source); current.gains.push(envelope);
      });
      setPhase('playing');
      let previousStage = -1;
      const tick = () => {
        if (generation.current !== ticket || session.current !== current) return;
        // Prefer the output-device timestamp; otherwise follow the AudioContext clock.
        const stamp = context.getOutputTimestamp?.();
        const outputTime = stamp?.contextTime ?? 0, outputTimestamp = stamp?.performanceTime ?? 0;
        const clock = outputTimestamp > 0 && outputTime > 0
          ? Math.min(context.currentTime, outputTime + (performance.now() - outputTimestamp) / 1000)
          : Math.max(0, context.currentTime - (context.outputLatency || 0));
        const elapsed = Math.max(0, clock - begins), clip = auditionClipAt(timeline, elapsed);
        if (clock >= begins && clip) {
          if (clip.stageIndex !== previousStage) { previousStage = clip.stageIndex; callbacks.current.onStage(clip.stageIndex); }
          setPosition({ stage: clip.stageIndex, repeat: clip.repeatIndex + 1, elapsed, duration: timeline.duration });
        }
        if (elapsed >= timeline.duration) {
          if (previousStage !== stages.length - 1) callbacks.current.onStage(stages.length - 1);
          stop(false); setPhase('idle');
          setPosition({ stage: stages.length - 1, repeat: repeats, elapsed: timeline.duration, duration: timeline.duration });
          return;
        }
        current.frame = requestAnimationFrame(tick);
      };
      tick();
    } catch (cause) {
      if (generation.current !== ticket) return;
      stop();
      setError(jp ? '音声を準備できませんでした。保存したステレオWAVとブラウザの音声出力を確認してください。' : 'Audio could not be prepared. Check the saved stereo WAVs and browser audio output.');
      if (cause instanceof Error && cause.name === 'NotAllowedError') setError(jp ? 'ブラウザが音声再生を許可しませんでした。再生ボタンをもう一度押してください。' : 'The browser did not allow audio playback. Press Play again.');
    }
  };
  const currentStage = position ? stages[position.stage] : undefined;
  const invalid = !stages.length || !Number.isFinite(gain) || gain < 0 || gain > 1;
  const busy = phase !== 'idle';

  return <section className="process-audition" aria-label={jp ? '復元過程を続けて聴く' : 'Listen through the reconstruction stages'}>
    <header><span>PROCESS / LISTEN</span><h3>{jp ? '復元過程を続けて聴く' : 'Hear the reconstruction evolve'}</h3>
      <p>{jp ? '保存済みの中間推定から最終結果へ、同じ短い音を順番に聴き比べます。聞こえている段階に3D表示を合わせます。' : 'Compare the same short sound through saved intermediate estimates and the final result. The 3D view follows the audible stage.'}</p></header>
    <div className="pa-controls"><button className="pa-play" type="button" disabled={!active || invalid || busy} onClick={() => void play()}>{phase === 'loading' ? (jp ? '音声を準備中…' : 'Preparing audio…') : (jp ? '過程を再生' : 'Play the process')} ▷</button>
      <button type="button" disabled={!busy} onClick={() => stop()}>{jp ? '停止' : 'Stop'} □</button>
      <label>{jp ? '各段階の繰り返し' : 'Repeats per stage'}<select value={repeats} disabled={busy} onChange={event => { setRepeats(Number(event.target.value)); setPosition(null); }}>{[1, 2, 4].map(value => <option key={value} value={value}>{value}{jp ? '回' : '×'}</option>)}</select></label></div>
    <div className="pa-stages" aria-label={jp ? '再生する段階' : 'Playback stages'}>{stages.map((stage, i) => <span key={stage.id} data-current={position?.stage === i}>{stage.stage === 'final_sample' ? (jp ? '最終' : 'Final') : `step ${stage.step}`}<small>σ {sigmaText(stage.sigma)}</small></span>)}</div>
    {position && <><progress className="pa-progress" value={position.elapsed} max={position.duration} aria-label={jp ? '試聴の再生位置' : 'Audition playback position'}/><output className="pa-readout" aria-live="polite">{currentStage?.stage === 'final_sample' ? (jp ? '最終結果' : 'Final result') : `step ${currentStage?.step}`} · {position.repeat}/{repeats} {jp ? '回' : 'repeats'} · {position.elapsed.toFixed(1)} / {position.duration.toFixed(1)} s</output></>}
    {error && <p className="pa-error">{error}</p>}
    {invalid && <p className="pa-error">{jp ? '試聴できる保存音声がまだありません。' : 'Saved audio is not yet available for this audition.'}</p>}
    <p className="pa-note">{jp ? 'これは保存した推定の連続試聴です。リアルタイム適応やオンライン学習ではありません。σは音声の時間ではありません。全段階に共通のゲインを適用し、各音の両端だけ約5msフェードします。段階同士の音は重ねません。' : 'This plays saved estimates in sequence; it is not real-time adaptation or online learning. σ is not audio time. Every stage uses the same gain, with about 5 ms fades at each clip edge. Different stages are not overlapped.'}</p>
  </section>;
}

export default ProcessAudition;
