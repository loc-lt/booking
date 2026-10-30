import {
	ApiError,
	type Booking,
	useApproveBooking,
	useRejectBooking,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { BookingCard } from '@booking-core/booking-ui';
import { Button, Input } from '@booking-core/ui';
import { useState } from 'react';

export function ApprovalRow({
	booking,
	resourceLabel,
	resourceTypeLabel,
	onChanged,
}: {
	booking: Booking;
	resourceLabel: string;
	resourceTypeLabel?: string;
	onChanged: () => void;
}) {
	const [rejecting, setRejecting] = useState(false);
	const [reason, setReason] = useState('');
	const approveBooking = useApproveBooking();
	const rejectBooking = useRejectBooking();
	const error = approveBooking.error ?? rejectBooking.error;

	function handleApprove() {
		approveBooking.mutate(
			{ bookingId: booking.id },
			{
				onSuccess: () => {
					trackEvent('booking_approved', { resourceTypeId: booking.resourceTypeId });
					onChanged();
				},
			},
		);
	}

	function handleReject() {
		rejectBooking.mutate(
			{ bookingId: booking.id, data: { reason } },
			{
				onSuccess: () => {
					trackEvent('booking_rejected', { resourceTypeId: booking.resourceTypeId });
					setRejecting(false);
					setReason('');
					onChanged();
				},
			},
		);
	}

	return (
		<div className='flex flex-col gap-2'>
			<BookingCard
				booking={booking}
				resourceLabel={
					resourceTypeLabel ? `${resourceLabel} · ${resourceTypeLabel}` : resourceLabel
				}
				actions={
					!rejecting && (
						<div className='flex gap-2'>
							<Button
								type='button'
								size='sm'
								disabled={approveBooking.isPending}
								onClick={handleApprove}
							>
								Approve
							</Button>
							<Button
								type='button'
								size='sm'
								variant='ghost'
								disabled={rejectBooking.isPending}
								onClick={() => setRejecting(true)}
							>
								Reject
							</Button>
						</div>
					)
				}
			/>
			{rejecting && (
				<div className='flex items-center gap-2 pl-4'>
					<Input
						placeholder='Reason shown to the member'
						value={reason}
						onChange={(e) => setReason(e.target.value)}
						className='flex-1'
					/>
					<Button
						type='button'
						size='sm'
						disabled={!reason.trim() || rejectBooking.isPending}
						onClick={handleReject}
					>
						{rejectBooking.isPending ? 'Rejecting…' : 'Confirm reject'}
					</Button>
					<Button type='button' size='sm' variant='ghost' onClick={() => setRejecting(false)}>
						Cancel
					</Button>
				</div>
			)}
			{error && (
				<p className='text-destructive pl-4 text-sm'>
					Couldn't update the booking ({error instanceof ApiError ? error.code : 'UNKNOWN_ERROR'}).
				</p>
			)}
		</div>
	);
}
