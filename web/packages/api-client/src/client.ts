export interface CoreClientConfig {
	baseUrl: string;
	getToken: () => string | null | undefined;
	getTenantId: () => string | null | undefined;
}

let config: CoreClientConfig = {
	baseUrl: '',
	getToken: () => null,
	getTenantId: () => null,
};

export function configureCoreClient(next: CoreClientConfig): void {
	config = next;
}

/** The tenant the client is currently configured for, e.g. for tagging tracking events. */
export function getConfiguredTenantId(): string | null | undefined {
	return config.getTenantId();
}

export class ApiError extends Error {
	status: number;
	code: string;
	body: unknown;

	constructor(status: number, code: string, body: unknown) {
		super(code);
		this.name = 'ApiError';
		this.status = status;
		this.code = code;
		this.body = body;
	}
}

export interface ApiFetchConfig {
	url: string;
	method: string;
	params?: Record<string, unknown>;
	data?: unknown;
	headers?: Record<string, string>;
	signal?: AbortSignal;
}

function buildUrl(url: string, params: Record<string, unknown> | undefined): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params ?? {})) {
		if (value !== undefined && value !== null) {
			search.append(key, String(value));
		}
	}
	const query = search.toString();
	return `${config.baseUrl}${url}${query ? `?${query}` : ''}`;
}

export async function apiFetch<T>({
	url,
	method,
	params,
	data,
	headers,
	signal,
}: ApiFetchConfig): Promise<T> {
	const requestHeaders = new Headers(headers);
	requestHeaders.set('Accept', 'application/json');

	const token = config.getToken();
	if (token) {
		requestHeaders.set('Authorization', `Bearer ${token}`);
	}

	const tenantId = config.getTenantId();
	if (tenantId) {
		requestHeaders.set('X-Tenant-Id', tenantId);
	}

	const requestInit: RequestInit = {
		method,
		headers: requestHeaders,
		body: data === undefined ? undefined : JSON.stringify(data),
		signal,
	};

	const response = await fetch(buildUrl(url, params), requestInit).catch((error) => {
		// jsdom's AbortController/AbortSignal (what TanStack Query constructs in
		// our component tests) isn't accepted by Node's native fetch, which
		// checks for its own AbortSignal class rather than whatever
		// globalThis.AbortSignal currently is. Harmless to retry without it —
		// cancellation just becomes a no-op, which never happens in a real
		// browser (one realm, no mismatch).
		if (signal && error instanceof TypeError && /AbortSignal/.test(error.message)) {
			return fetch(buildUrl(url, params), { ...requestInit, signal: undefined });
		}
		throw error;
	});

	if (!response.ok) {
		const body = await response.json().catch(() => null);
		throw new ApiError(response.status, body?.code ?? 'UNKNOWN_ERROR', body);
	}

	if (response.status === 204) {
		return undefined as T;
	}

	return response.json() as Promise<T>;
}
