import { ApiError, useListResourceTypes } from '@booking-core/api-client';
import { Skeleton } from '@booking-core/ui';
import { ResourceTypeCard } from './resource-type-card';

export function ResourceTypesList() {
	const { data, isPending, error } = useListResourceTypes();

	if (isPending) {
		return (
			<div className='flex flex-col gap-2'>
				<Skeleton className='h-20 w-full' />
				<Skeleton className='h-20 w-full' />
			</div>
		);
	}

	if (error) {
		const code = error instanceof ApiError ? error.code : 'UNKNOWN_ERROR';
		return <p className='text-destructive text-sm'>Couldn't load resource types ({code}).</p>;
	}

	if (data.data.length === 0) {
		return <p className='text-muted-foreground text-sm'>No resource types yet.</p>;
	}

	return (
		<div className='flex flex-col gap-3'>
			{data.data.map((resourceType) => (
				<ResourceTypeCard key={resourceType.id} resourceType={resourceType} />
			))}
		</div>
	);
}
