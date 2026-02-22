interface Props {
  className?: string;
}

export default function Skeleton({ className = "" }: Props) {
  return <div className={`skeleton ${className}`.trim()} aria-hidden="true" />;
}
