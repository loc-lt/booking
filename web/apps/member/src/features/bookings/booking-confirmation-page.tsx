import { ApiError, useGetBooking, useListResources } from '@booking-core/api-client';
import { BookingCard } from '@booking-core/booking-ui';
import { Skeleton } from '@booking-core/ui';
import { Link } from '@tanstack/react-router';

export function BookingConfirmationPage({ bookingId }: { bookingId: string }) {
	const bookingQuery = useGetBooking(bookingId);
	const resourcesQuery = useListResources();

	if (bookingQuery.isPending) {
		return (
			<div className='mx-auto flex max-w-2xl flex-col gap-4 p-6'>
				<Skeleton className='h-32 w-full' />
			</div>
		);
	}

	if (bookingQuery.error) {
		const code = bookingQuery.error instanceof ApiError ? bookingQuery.error.code : 'UNKNOWN_ERROR';
		return (
			<div className='mx-auto flex max-w-2xl flex-col gap-4 p-6'>
				<p className='text-destructive text-sm'>Couldn't load this booking ({code}).</p>
			</div>
		);
	}

	const booking = bookingQuery.data;
	const resourceLabel = resourcesQuery.data?.data.find(
		(resource) => resource.id === booking.resourceId,
	)?.label;
	const isDenied = booking.status === 'rejected';

	return (
		<div className='mx-auto flex max-w-2xl flex-col gap-4 p-6'>
			<h1 className='text-xl font-semibold'>
				{isDenied ? "Booking couldn't be confirmed" : 'Booking confirmed'}
			</h1>
			<BookingCard booking={booking} resourceLabel={resourceLabel} />
			{booking.status === 'pending_approval' && (
				<p className='text-muted-foreground text-sm'>
					This resource type needs approval — you'll be notified once it's reviewed.
				</p>
			)}
			<Link to='/bookings' className='text-sm hover:underline'>
				View my bookings →
			</Link>
		</div>
	);
}
