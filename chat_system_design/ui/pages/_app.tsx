import type { AppProps } from 'next/app';
import '../styles/globals.css';
import 'uikit/dist/css/uikit.min.css';
import 'uikit/dist/js/uikit.min.js';
import 'uikit/dist/js/uikit-icons.min.js';

export default function MyApp({ Component, pageProps }: AppProps) {
    return <Component {...pageProps} />;
}
