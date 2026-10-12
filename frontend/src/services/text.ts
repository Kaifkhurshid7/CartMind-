/** Removes emoji and pictographs; the UI uses icons instead. */
export function stripEmoji(text: string): string {
  return text
    .replace(/[\p{Extended_Pictographic}\u{FE0F}\u{200D}]/gu, '')
    .replace(/^[\s]+/, '')
    .replace(/[ \t]{2,}/g, ' ')
}
