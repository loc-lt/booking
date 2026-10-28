// Placeholder until the auth service is wired up (see docs/architecture.md).
// Mocks don't check the token or tenant, so a fixed demo tenant is enough to
// build and verify screens.
const DEMO_TENANT_ID = '0193f4c1-0000-7000-8000-000000000001';

export const auth = {
	getAccessToken: (): string | null => null,
	currentTenantId: (): string => DEMO_TENANT_ID,
};
