import type { Tone } from "./types";

/**
 * !NOTE: Department.colorはバックエンドAPI(ojt_seed.py)が返す生のhex値であり、
 *        CSS変数ではないためダークモードに自動追従しない。ここでバックエンドの
 *        既知のhex値をフロントエンドのアクセント色相(Tone)へ逆引きし、
 *        DeptCardは常にtheme.palette.accent[tone]経由で描画する。
 */
const HEX_TO_TONE: Record<string, Tone> = {
  "#d6ebff": "blue",
  "#cdeede": "green",
  "#ffd9e6": "pink",
  "#e3ddff": "purple",
  "#ffe9c7": "orange",
};

export function toneForDeptColor(hex: string): Tone | null {
  return HEX_TO_TONE[hex.toLowerCase()] ?? null;
}
