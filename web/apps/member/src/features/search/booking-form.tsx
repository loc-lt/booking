import {
	ApiError,
	type AvailabilitySlot,
	type Booking,
	type FieldDefinition,
	getSearchAvailabilityQueryKey,
	useCreateBooking,
	useListResources,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { CustomFieldValuesEditor } from '@booking-core/custom-fields';
import { Button } from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

export function BookingForm({
	resourceId,
	resourceTypeId,
	siteId,
	date,
	fields,
	slot,
	onBooked,
}: {
	resourceId: string;
	resourceTypeId: string;
	siteId: string;
	date: string;
	fields: FieldDefinition[];
	slot: AvailabilitySlot;
	onBooked: (booking: Booking) => void;
}) {
	const queryClient = useQueryClient();
	const [values, setValues] = useState<Record<string, unknown>>({});
	const createBooking = useCreateBooking();
	const allResourcesQuery = useListResources();
	const referenceOptions: Record<string, { value: string; label: string }[]> = {};
	for (const resource of allResourcesQuery.data?.data ?? []) {
		const existing = referenceOptions[resource.resourceTypeId] ?? [];
		existing.push({ value: resource.id, label: resource.label });
		referenceOptions[resource.resourceTypeId] = existing;
	}

	function handleSubmit() {
		createBooking.mutate(
			{ data: { resourceId, start: slot.start, end: slot.end, customFieldValues: values } },
			{
				onSuccess: (booking) => {
					const durationMinutes =
						(new Date(slot.end).getTime() - new Date(slot.start).getTime()) / 60_000;
					trackEvent('booking_submitted', { resourceTypeId, durationMinutes });
					setValues({});
					onBooked(booking);
				},
				onError: (error) => {
					if (error instanceof ApiError && error.code === 'SLOT_TAKEN') {
						queryClient.invalidateQueries({
							queryKey: getSearchAvailabilityQueryKey({ siteId, resourceTypeId, resourceId, date }),
						});
					}
				},
			},
		);
	}

	const error = createBooking.error;
	const validationErrors =
		error instanceof ApiError && error.code === 'VALIDATION_FAILED'
			? Object.fromEntries(
					((error.body as { errors?: { field: string; message: string }[] }).errors ?? []).map(
						(fieldError) => [fieldError.field, fieldError.message],
					),
				)
			: undefined;
	const reasons =
		error instanceof ApiError && error.code === 'BOOKING_DENIED'
			? (error.body as { reasons?: { ruleId: string; message: string }[] }).reasons
			: undefined;

	return (
		<div className='flex flex-col gap-3 border-t pt-3'>
			<CustomFieldValuesEditor
				fields={fields}
				values={values}
				onChange={setValues}
				errors={validationErrors}
				referenceOptions={referenceOptions}
			/>

			{error instanceof ApiError && error.code === 'SLOT_TAKEN' && (
				<p className='text-destructive text-sm'>Someone just took this slot — pick another.</p>
			)}
			{reasons && reasons.length > 0 && (
				<ul className='text-destructive text-sm'>
					{reasons.map((reason) => (
						<li key={reason.ruleId}>{reason.message}</li>
					))}
				</ul>
			)}
			{error instanceof ApiError &&
				error.code !== 'SLOT_TAKEN' &&
				error.code !== 'BOOKING_DENIED' &&
				error.code !== 'VALIDATION_FAILED' && (
					<p className='text-destructive text-sm'>Couldn't submit the booking ({error.code}).</p>
				)}

			<Button type='button' onClick={handleSubmit} disabled={createBooking.isPending}>
				{createBooking.isPending ? 'Booking…' : 'Book this slot'}
			</Button>
		</div>
	);
}
