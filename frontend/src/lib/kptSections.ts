export type KptKey = "keep" | "problem" | "try";

export interface KptSection {
  key: KptKey;
  label: string;
  icon: string;
  accent: string;
  iconBg: string;
  iconColor: string;
  labelColor: string;
  borderColor: string;
  bgColor: string;
  description: string;
  placeholder: string;
}

export const KPT_SECTIONS: KptSection[] = [
  {
    key: "keep",
    label: "Keep",
    icon: "ph-fill ph-thumbs-up",
    accent: "var(--color-green-300)",
    iconBg: "var(--color-green-100)",
    iconColor: "var(--color-green-500)",
    labelColor: "var(--color-green-500)",
    borderColor: "var(--color-green-100)",
    bgColor: "var(--color-green-100)",
    description: "うまくいった・続けたいこと",
    placeholder: "例）朝イチでタスクを整理したら集中できた",
  },
  {
    key: "problem",
    label: "Problem",
    icon: "ph-fill ph-warning",
    accent: "var(--color-pink-300)",
    iconBg: "var(--color-pink-100)",
    iconColor: "var(--color-pink-500)",
    labelColor: "var(--color-pink-500)",
    borderColor: "var(--color-pink-100)",
    bgColor: "var(--color-pink-100)",
    description: "うまくいかなかったこと",
    placeholder: "例）会議の発言タイミングがつかめなかった",
  },
  {
    key: "try",
    label: "Try",
    icon: "ph-fill ph-rocket-launch",
    accent: "var(--color-purple-400)",
    iconBg: "var(--color-purple-100)",
    iconColor: "var(--color-purple-500)",
    labelColor: "var(--color-purple-500)",
    borderColor: "var(--color-purple-100)",
    bgColor: "var(--color-purple-100)",
    description: "次に試したいこと",
    placeholder: "例）次の会議で1回は質問してみる",
  },
];
