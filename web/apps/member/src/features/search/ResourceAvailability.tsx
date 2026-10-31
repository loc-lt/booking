import {
	ApiError,
	type AvailabilitySlot,
	type Booking,
	type FieldDefinition,
	useSearchAvailability,
} from '@booking-core/api-client';
import { AvailabilityGrid } from '@booking-core/booking-ui';
import { DatePicker, Skeleton } from '@booking-core/ui';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { BookingForm } from './BookingForm';

// A site picker isn't built yet, so availability is always shown for this fixed demo site.
const DEMO_SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const DEFAULT_DATE = '2026-12-15';

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
	const [date, setDate] = useState(DEFAULT_DATE);
	const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot>();
	const { data, isPending, error } = useSearchAvailability({
		date,
		resourceId,
		resourceTypeId,
		siteId: DEMO_SITE_ID,
	});

	function handleBooked(booking: Booking) {
		setSelectedSlot(undefined);
		navigate({ to: '/bookings/$bookingId', params: { bookingId: booking.id } });
	}

	return (
		<div className='flex flex-col gap-3'>
			<DatePicker
				className='w-40'
				clearLabel='Clear'
				onValueChange={(value) => {
					// Clearing just re-shows the last selected date instead of an empty
					// query — the API requires a date, so there's no "no date" state.
					if (value === '') {
						return;
					}

					setDate(value);
					setSelectedSlot(undefined);
				}}
				placeholder='Pick a date'
				submitLabel='Apply'
				value={date}
			/>

			{isPending ? (
				<Skeleton className='h-9 w-full' />
			) : error ? (
				<p className='text-destructive text-sm'>
					Couldn't load availability ({error instanceof ApiError ? error.code : 'UNKNOWN_ERROR'}).
				</p>
			) : data ? (
				<>
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
							date={date}
							fields={fields}
							slot={selectedSlot}
							onBooked={handleBooked}
						/>
					)}
				</>
			) : null}
		</div>
	);
}
