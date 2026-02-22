import type { ButtonHTMLAttributes, PropsWithChildren } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export default function Button({
  children,
  className = "",
  variant = "secondary",
  size = "md",
  ...props
}: PropsWithChildren<Props>) {
  return (
    <button
      className={`ui-btn ui-btn-${variant} ui-btn-${size} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}
