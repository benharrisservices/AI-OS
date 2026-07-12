/**
 * Resolves a chapter id to its audio file. Every chapter binds to
 * `/audio/{id}.mp3`. Replace the placeholder files with ElevenLabs
 * exports of the same name and nothing else needs to change.
 */
export function audioSrc(chapterId: string): string {
  return `/audio/${chapterId}.mp3`;
}
