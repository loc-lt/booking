// Placeholder until the auth service is wired up (see docs/architecture.md).
// Mocks don't check the token, tenant or member, so fixed demo ids are enough
// to build and verify screens. DEMO_MEMBER_ID matches the mocks' seeded
// member (bookingsOperations.ts), so bookings created there show as "mine".
const DEMO_TENANT_ID = '0193f4c1-0000-7000-8000-000000000001';
const DEMO_MEMBER_ID = '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e';

export const auth = {
	getAccessToken: (): string | null => null,
	currentTenantId: (): string => DEMO_TENANT_ID,
	currentMemberId: (): string => DEMO_MEMBER_ID,
};
