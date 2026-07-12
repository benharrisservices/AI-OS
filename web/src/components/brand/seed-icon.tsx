import type { SVGProps } from "react";

/**
 * sedr brand mark — a simple, modern seed. Flat, single-color (currentColor),
 * recognizable at favicon size.
 */
export function SeedIcon({
  className,
  ...props
}: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className={className}
      {...props}
    >
      <path d="M17.5 3.2c.6-.3 1.3.2 1.2.9-.5 4.3-1.8 8.9-5 12.1a8.2 8.2 0 0 1-9.4 1.6c-.5-.3-.6-1-.2-1.4C7.4 12.9 12.3 5.6 17.5 3.2Z" />
      <path
        d="M5 19c2.8-3.9 6.3-7.2 10.3-9.6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        opacity="0.35"
      />
    </svg>
  );
}
