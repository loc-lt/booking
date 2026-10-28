import { createFileRoute } from '@tanstack/react-router';
import { ResourceTypesPage } from '@/features/resource-types';

export const Route = createFileRoute('/resource-types')({
	component: ResourceTypesPage,
});
