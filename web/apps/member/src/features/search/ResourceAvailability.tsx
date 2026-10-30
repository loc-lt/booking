import {
	ApiError,
	type AvailabilitySlot,
	type Booking,
	type FieldDefinition,
	useSearchAvailability,
} from '@booking-core/api-client';
import { AvailabilityGrid } from '@booking-core/booking-ui';
import { Skeleton } from '@booking-core/ui';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { BookingForm } from './BookingForm';

// Sites and a real date picker aren't built yet, so availability is shown for this fixed
// demo site and day.
const DEMO_SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const DEMO_DATE = '2026-12-15';

export function ResourceAvailability({
	resourceId,
	resourceTypeId,
	fields,
}: {
	resourceId: string;
	resourceTypeId: string;
	fields: FieldDefinition[];
}) {
	const navigate = useNavigate();
	const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot>();
	const { data, isPending, error } = useSearchAvailability({
		siteId: DEMO_SITE_ID,
		resourceTypeId,
		resourceId,
		date: DEMO_DATE,
	});

	function handleBooked(booking: Booking) {
		setSelectedSlot(undefined);
		navigate({ to: '/bookings/$bookingId', params: { bookingId: booking.id } });
	}

	if (isPending) {
		return <Skeleton className='h-9 w-full' />;
	}

	if (error) {
		const code = error instanceof ApiError ? error.code : 'UNKNOWN_ERROR';
		return <p className='text-destructive text-sm'>Couldn't load availability ({code}).</p>;
	}

	return (
		<div className='flex flex-col gap-3'>
			<AvailabilityGrid
				slots={data.slots}
				selectedSlot={selectedSlot}
				onSelectSlot={setSelectedSlot}
			/>
			{selectedSlot && (
				<BookingForm
					resourceId={resourceId}
					resourceTypeId={resourceTypeId}
					siteId={DEMO_SITE_ID}
					date={DEMO_DATE}
					fields={fields}
					slot={selectedSlot}
					onBooked={handleBooked}
				/>
			)}
		</div>
	);
}
