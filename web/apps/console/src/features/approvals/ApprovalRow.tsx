import {
	ApiError,
	type Booking,
	useApproveBooking,
	useRejectBooking,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { BookingCard } from '@booking-core/booking-ui';
import { Button, ConfirmationModal, Input } from '@booking-core/ui';
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
				}
			/>
			<ConfirmationModal
				cancelLabel='Cancel'
				confirmDisabled={!reason.trim()}
				confirmLabel='Reject'
				dangerous
				isConfirming={rejectBooking.isPending}
				onConfirm={handleReject}
				onOpenChange={setRejecting}
				open={rejecting}
				title='Reject booking'
			>
				<Input
					onChange={(e) => setReason(e.target.value)}
					placeholder='Reason shown to the member'
					value={reason}
				/>
			</ConfirmationModal>
			{error && (
				<p className='text-destructive pl-4 text-sm'>
					Couldn't update the booking ({error instanceof ApiError ? error.code : 'UNKNOWN_ERROR'}).
				</p>
			)}
		</div>
	);
}
