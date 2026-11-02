import type { Booking } from '@booking-core/api-client';
import { BookingCard, BookingTimeline } from '@booking-core/booking-ui';

export function BookingRow({
	booking,
	resourceLabel,
	expanded,
	onToggle,
}: {
	booking: Booking;
	resourceLabel: string;
	expanded: boolean;
	onToggle: () => void;
}) {
	return (
		<div className='flex flex-col gap-2'>
			<BookingCard booking={booking} resourceLabel={resourceLabel} onClick={onToggle} />
			{expanded && (
				<div className='pl-4'>
					<BookingTimeline history={booking.history} />
				</div>
			)}
		</div>
	);
}
