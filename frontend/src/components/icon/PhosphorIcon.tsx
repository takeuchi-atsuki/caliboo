export interface PhosphorIconProps {
  name: string;
  size?: number;
  color?: string;
  className?: string;
}

export function PhosphorIcon({ name, size, color, className }: PhosphorIconProps) {
  return <i className={[name, className].filter(Boolean).join(" ")} style={{ fontSize: size, color }} />;
}
