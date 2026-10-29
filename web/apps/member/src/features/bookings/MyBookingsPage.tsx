import {
	ApiError,
	getListBookingsQueryKey,
	useListBookings,
	useListResources,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { Skeleton } from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { BookingRow } from './BookingRow';

export function MyBookingsPage() {
	const queryClient = useQueryClient();
	const [expandedId, setExpandedId] = useState<string>();
	const bookingsQuery = useListBookings();
	const resourcesQuery = useListResources();

	useEffect(() => {
		if (bookingsQuery.data) {
			trackEvent('my_bookings_viewed', { resultsCount: bookingsQuery.data.data.length });
		}
	}, [bookingsQuery.data]);

	const resourceLabelsById = new Map(
		(resourcesQuery.data?.data ?? []).map((resource) => [resource.id, resource.label]),
	);

	function handleChanged() {
		queryClient.invalidateQueries({ queryKey: getListBookingsQueryKey() });
	}

	return (
		<div className='mx-auto flex max-w-2xl flex-col gap-4 p-6'>
			<h1 className='text-xl font-semibold'>My bookings</h1>

			{bookingsQuery.isPending && (
				<div className='flex flex-col gap-2'>
					<Skeleton className='h-24 w-full' />
					<Skeleton className='h-24 w-full' />
				</div>
			)}

			{bookingsQuery.error && (
				<p className='text-destructive text-sm'>
					Couldn't load your bookings (
					{bookingsQuery.error instanceof ApiError ? bookingsQuery.error.code : 'UNKNOWN_ERROR'}
					).
				</p>
			)}

			{bookingsQuery.data && bookingsQuery.data.data.length === 0 && (
				<p className='text-muted-foreground text-sm'>No bookings yet.</p>
			)}

			{bookingsQuery.data?.data.map((booking) => (
				<BookingRow
					key={booking.id}
					booking={booking}
					resourceLabel={resourceLabelsById.get(booking.resourceId) ?? 'Resource'}
					expanded={expandedId === booking.id}
					onToggle={() =>
						setExpandedId((current) => (current === booking.id ? undefined : booking.id))
					}
					onChanged={handleChanged}
				/>
			))}
		</div>
	);
}
