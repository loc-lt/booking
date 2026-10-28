export interface ApiClientConfig {
	baseUrl: string;
	getAccessToken: () => string | null | undefined;
	getTenantId: () => string | null | undefined;
}

let config: ApiClientConfig = {
	baseUrl: '',
	getAccessToken: () => null,
	getTenantId: () => null,
};

export function configureApiClient(next: ApiClientConfig): void {
	config = next;
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

	const token = config.getAccessToken();
	if (token) {
		requestHeaders.set('Authorization', `Bearer ${token}`);
	}

	const tenantId = config.getTenantId();
	if (tenantId) {
		requestHeaders.set('X-Tenant-Id', tenantId);
	}

	const response = await fetch(buildUrl(url, params), {
		method,
		headers: requestHeaders,
		body: data === undefined ? undefined : JSON.stringify(data),
		signal,
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
