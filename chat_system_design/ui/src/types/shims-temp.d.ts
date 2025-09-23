/**
 * Temporary shim declarations to suppress TypeScript errors ("Cannot find module 'react'", JSX intrinsic elements not found, etc.)
 * BEFORE running `npm install`. Remove this file after dependencies are installed and proper @types packages are available.
 */

// Basic React namespace & FC placeholder
declare namespace React {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  type ReactNode = any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  interface FC<P = Record<string, any>> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (props: P & { children?: ReactNode }): any;
  }
}

// Allow any JSX intrinsic element so JSX compiles
declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

// Lightweight module stubs (resolved after real packages installed)
declare module 'react' {
  export = React;
}
declare module 'react-dom' {
  const ReactDOM: any; // eslint-disable-line @typescript-eslint/no-explicit-any
  export default ReactDOM;
}
declare module 'next' {
  const x: any;
  export = x;
} // eslint-disable-line @typescript-eslint/no-explicit-any
declare module 'next/*' {
  const x: any;
  export = x;
} // eslint-disable-line @typescript-eslint/no-explicit-any
declare module 'next/app' {
  const x: any;
  export = x;
}
declare module 'next/router' {
  const x: any;
  export = x;
}
declare module 'next/link' {
  const x: any;
  export = x;
}
declare module 'react-icons/fa' {
  export const FaClock: any;
  export const FaCheck: any;
  export const FaCheckDouble: any;
}
declare module 'clsx' {
  export default function clsx(...args: any[]): string;
} // eslint-disable-line @typescript-eslint/no-explicit-any
declare module 'uikit/dist/css/uikit.min.css';
declare module 'uikit/dist/js/uikit.min.js';
declare module 'uikit/dist/js/uikit-icons.min.js';

// Node.js process shim (very loose)
declare const process: { env: Record<string, string | undefined> };

// NOTE: Remove this file after running `npm install` to get real type safety.
