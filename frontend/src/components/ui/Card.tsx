import type { PropsWithChildren } from "react";

interface Props {
  title?: string;
  subtitle?: string;
  className?: string;
}

export default function Card({ title, subtitle, className = "", children }: PropsWithChildren<Props>) {
  return (
    <section className={`card glass ${className}`.trim()}>
      {(title || subtitle) && (
        <div className="card-head">
          {title && <h3>{title}</h3>}
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
      )}
      {children}
    </section>
  );
}
