import {
	ApiError,
	getListBookingsQueryKey,
	type ResourceType,
	useListBookings,
	useListResources,
	useListResourceTypes,
} from '@booking-core/api-client';
import { Skeleton } from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { ApprovalRow } from './ApprovalRow';

export function ApprovalsPage() {
	const queryClient = useQueryClient();
	const bookingsQuery = useListBookings({ status: 'pending_approval' });
	const resourcesQuery = useListResources();
	const resourceTypesQuery = useListResourceTypes();

	const resourceLabelsById = new Map(
		(resourcesQuery.data?.data ?? []).map((resource) => [resource.id, resource.label]),
	);
	const resourceTypesById = new Map<string, ResourceType>(
		(resourceTypesQuery.data?.data ?? []).map((type) => [type.id, type]),
	);

	function handleChanged() {
		queryClient.invalidateQueries({
			queryKey: getListBookingsQueryKey({ status: 'pending_approval' }),
		});
	}

	return (
		<div className='mx-auto flex max-w-2xl flex-col gap-4 p-6'>
			<h1 className='text-xl font-semibold'>Approvals</h1>

			{bookingsQuery.isPending && (
				<div className='flex flex-col gap-2'>
					<Skeleton className='h-24 w-full' />
					<Skeleton className='h-24 w-full' />
				</div>
			)}

			{bookingsQuery.error && (
				<p className='text-destructive text-sm'>
					Couldn't load approvals (
					{bookingsQuery.error instanceof ApiError ? bookingsQuery.error.code : 'UNKNOWN_ERROR'}
					).
				</p>
			)}

			{bookingsQuery.data && bookingsQuery.data.data.length === 0 && (
				<p className='text-muted-foreground text-sm'>Nothing waiting on approval.</p>
			)}

			{bookingsQuery.data?.data.map((booking) => (
				<ApprovalRow
					key={booking.id}
					booking={booking}
					resourceLabel={resourceLabelsById.get(booking.resourceId) ?? 'Resource'}
					resourceTypeLabel={resourceTypesById.get(booking.resourceTypeId)?.label}
					onChanged={handleChanged}
				/>
			))}
		</div>
	);
}
