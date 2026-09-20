export function posToPlainOffset(doc: { textBetween: (from: number, to: number, blockSep: string) => string }, pos: number): number {
  return doc.textBetween(0, pos, "\n").length;
}

export function selectionToPlainRange(
  doc: { textBetween: (from: number, to: number, blockSep: string) => string },
  from: number,
  to: number,
): { start: number; end: number; text: string } | null {
  if (from === to) return null;
  const start = posToPlainOffset(doc, from);
  const end = posToPlainOffset(doc, to);
  const text = doc.textBetween(from, to, "\n");
  return { start, end, text };
}
