import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from './client';

function jsonResponse(body: unknown, status = 200) {
	return new Response(JSON.stringify(body), {
		status,
		headers: { 'Content-Type': 'application/json' },
	});
}

describe('apiFetch', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('retries without the signal when fetch rejects with a cross-realm AbortSignal mismatch', async () => {
		const fetchMock = vi
			.fn()
			.mockRejectedValueOnce(
				new TypeError(
					'RequestInit: Expected signal ("AbortSignal {}") to be an instance of AbortSignal.',
				),
			)
			.mockResolvedValueOnce(jsonResponse({ ok: true }));
		vi.stubGlobal('fetch', fetchMock);

		const result = await apiFetch({
			url: '/thing',
			method: 'GET',
			signal: new AbortController().signal,
		});

		expect(result).toEqual({ ok: true });
		expect(fetchMock).toHaveBeenCalledTimes(2);
		expect(fetchMock.mock.calls[1]?.[1]?.signal).toBeUndefined();
	});

	it('does not swallow an unrelated TypeError', async () => {
		const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch'));
		vi.stubGlobal('fetch', fetchMock);

		await expect(
			apiFetch({ url: '/thing', method: 'GET', signal: new AbortController().signal }),
		).rejects.toThrow('Failed to fetch');
		expect(fetchMock).toHaveBeenCalledTimes(1);
	});
});
