import { ApiError } from '@booking-core/api-client';

/** A mutation/query error's stable `code` ([docs/api.md](../../../../docs/api.md)), or a fallback for anything else (a network failure, a thrown non-`ApiError`). */
export function getErrorCode(error: unknown): string {
	return error instanceof ApiError ? error.code : 'UNKNOWN_ERROR';
}
