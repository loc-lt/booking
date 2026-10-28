import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(cleanup);

// app-kit's trackEvent/getRuntimeConfig read window.__CONFIG__, which only
// real app entry points set up via config.js. Give tests the same mock-mode
// defaults so tracking calls no-op to console.debug instead of throwing.
(window as unknown as { __CONFIG__: unknown }).__CONFIG__ = {
	app: 'test',
	apiUrl: '',
	apiMode: 'mock',
	posthogKey: '',
	sentryDsn: '',
};
