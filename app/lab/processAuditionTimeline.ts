export type AuditionClip = { stageIndex: number; repeatIndex: number; start: number; end: number; fade: number };
export type AuditionTimeline = { clips: AuditionClip[]; duration: number };

/** Contiguous clips, without crossfading different reconstructions together. */
export function buildAuditionTimeline(durations: number[], repeats: number): AuditionTimeline {
  if (![1, 2, 4].includes(repeats) || !durations.length || durations.some(value => !Number.isFinite(value) || value <= 0)) {
    throw new Error('Expected positive clip durations and 1, 2 or 4 repeats');
  }
  let cursor = 0;
  const clips: AuditionClip[] = [];
  durations.forEach((duration, stageIndex) => {
    for (let repeatIndex = 0; repeatIndex < repeats; repeatIndex++) {
      const end = cursor + duration;
      clips.push({ stageIndex, repeatIndex, start: cursor, end, fade: Math.min(.005, duration / 4) });
      cursor = end;
    }
  });
  return { clips, duration: cursor };
}

/** Half-open intervals: a shared boundary belongs to the next clip. */
export function auditionClipAt(timeline: AuditionTimeline, seconds: number): AuditionClip | undefined {
  if (!Number.isFinite(seconds) || seconds < 0 || seconds >= timeline.duration) return undefined;
  return timeline.clips.find(clip => seconds >= clip.start && seconds < clip.end);
}
