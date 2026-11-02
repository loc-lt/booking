import { ApiError } from '@booking-core/api-client';
import { describe, expect, it } from 'vitest';
import { getErrorCode } from './api-error';

describe('getErrorCode', () => {
	it("returns the ApiError's own code", () => {
		const error = new ApiError(409, 'SLOT_TAKEN', {
			type: 'about:blank',
			title: 'Slot taken',
			status: 409,
			code: 'SLOT_TAKEN',
		});
		expect(getErrorCode(error)).toBe('SLOT_TAKEN');
	});

	it('falls back to UNKNOWN_ERROR for a plain Error', () => {
		expect(getErrorCode(new Error('network down'))).toBe('UNKNOWN_ERROR');
	});

	it('falls back to UNKNOWN_ERROR for a non-Error throw', () => {
		expect(getErrorCode('nope')).toBe('UNKNOWN_ERROR');
		expect(getErrorCode(undefined)).toBe('UNKNOWN_ERROR');
		expect(getErrorCode(null)).toBe('UNKNOWN_ERROR');
	});
});
