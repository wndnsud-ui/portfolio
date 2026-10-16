const DIGIT_HAS_FINAL = [true, true, false, true, false, false, true, true, true, false]; // 영일이삼사오육칠팔구

function hasFinal(word: string): boolean {
  const ch = word.trim().slice(-1);
  if (!ch) return false;
  const code = ch.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 !== 0;
  if (/[0-9]/.test(ch)) return DIGIT_HAS_FINAL[Number(ch)];
  return /[lmnr]/i.test(ch);
}

/** 받침에 맞는 조사를 붙인다. josa('혜영', '을/를') → '혜영을' */
export function josa(word: string, pair: '을/를' | '은/는' | '이/가' | '과/와'): string {
  const [withFinal, without] = pair.split('/');
  return word + (hasFinal(word) ? withFinal : without);
}
