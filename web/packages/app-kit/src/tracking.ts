import { getConfiguredTenantId } from '@booking-core/api-client';
import * as Sentry from '@sentry/react';
import posthog from 'posthog-js';
import { getRuntimeConfig } from './config';

let initialized = false;

/**
 * Starts PostHog and Sentry when their keys are configured. Safe to call
 * every render — only runs once. See docs/analytics.md for naming and the
 * tracking plan.
 */
export function initTracking(appName: string): void {
	if (initialized) return;
	initialized = true;

	const config = getRuntimeConfig();

	if (config.posthogKey) {
		posthog.init(config.posthogKey, {
			api_host: 'https://app.posthog.com',
			person_profiles: 'identified_only',
		});
		posthog.register({ app: appName, tenantId: getConfiguredTenantId() });
	}

	if (config.sentryDsn) {
		Sentry.init({ dsn: config.sentryDsn, environment: appName });
	}
}

/**
 * Tracks a screen event per docs/analytics.md's naming convention
 * (`object_action`, snake_case, past tense). Without a configured PostHog
 * key — local dev on mocks — this logs to the console instead, so the
 * instrumentation is visible without a live project.
 */
export function trackEvent(name: string, properties?: Record<string, unknown>): void {
	if (getRuntimeConfig().posthogKey) {
		posthog.capture(name, properties);
	} else {
		console.debug('[tracking]', name, properties);
	}
}

/** Reports an error to Sentry when configured; always a safe no-op otherwise. */
export function captureError(error: unknown): void {
	if (getRuntimeConfig().sentryDsn) {
		Sentry.captureException(error);
	}
}
