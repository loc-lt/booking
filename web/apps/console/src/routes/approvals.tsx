import { createFileRoute } from '@tanstack/react-router';
import { ApprovalsPage } from '@/features/approvals';

export const Route = createFileRoute('/approvals')({
	component: ApprovalsPage,
});
