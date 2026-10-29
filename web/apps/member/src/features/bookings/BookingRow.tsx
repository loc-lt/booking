import {
	ApiError,
	type Booking,
	useCancelBooking,
	useCheckInBooking,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { BookingCard, BookingTimeline } from '@booking-core/booking-ui';
import { Button } from '@booking-core/ui';

const CANCELLABLE_STATUSES = new Set(['awaiting_payment', 'pending_approval', 'confirmed']);

export function BookingRow({
	booking,
	resourceLabel,
	expanded,
	onToggle,
	onChanged,
}: {
	booking: Booking;
	resourceLabel: string;
	expanded: boolean;
	onToggle: () => void;
	onChanged: () => void;
}) {
	const cancelBooking = useCancelBooking();
	const checkInBooking = useCheckInBooking();

	const canCheckIn = booking.status === 'confirmed';
	const canCancel = CANCELLABLE_STATUSES.has(booking.status);
	const error = checkInBooking.error ?? cancelBooking.error;

	return (
		<div className='flex flex-col gap-2'>
			<BookingCard
				booking={booking}
				resourceLabel={resourceLabel}
				onClick={onToggle}
				actions={
					<div className='flex gap-2'>
						{canCheckIn && (
							<Button
								type='button'
								size='sm'
								variant='outline'
								disabled={checkInBooking.isPending}
								onClick={(event) => {
									event.stopPropagation();
									checkInBooking.mutate(
										{ bookingId: booking.id },
										{
											onSuccess: () => {
												trackEvent('booking_checked_in', {
													resourceTypeId: booking.resourceTypeId,
												});
												onChanged();
											},
										},
									);
								}}
							>
								Check in
							</Button>
						)}
						{canCancel && (
							<Button
								type='button'
								size='sm'
								variant='ghost'
								disabled={cancelBooking.isPending}
								onClick={(event) => {
									event.stopPropagation();
									cancelBooking.mutate(
										{ bookingId: booking.id },
										{
											onSuccess: () => {
												trackEvent('booking_cancelled', {
													resourceTypeId: booking.resourceTypeId,
												});
												onChanged();
											},
										},
									);
								}}
							>
								Cancel
							</Button>
						)}
					</div>
				}
			/>
			{error && (
				<p className='text-destructive text-sm'>
					Couldn't update the booking ({error instanceof ApiError ? error.code : 'UNKNOWN_ERROR'}
					).
				</p>
			)}
			{expanded && (
				<div className='pl-4'>
					<BookingTimeline history={booking.history} />
				</div>
			)}
		</div>
	);
}
