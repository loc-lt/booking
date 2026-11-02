import type { Booking, BookingStatus, FieldDefinition } from '@booking-core/api-client';
import { FieldValueView, type ReferenceOption } from '@booking-core/custom-fields';
import { Button, ClearableInput, ConfirmationModal, Icon } from '@booking-core/ui';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { BookingStatusBadge } from './booking-status-badge';
import { isCheckInOpen } from './check-in-window';
import { formatTimeRange } from './format-date-time';

export interface BookingDetailsPanelProps {
	booking: Booking;
	/** Shown as the title; falls back to a generic placeholder when omitted. */
	resourceLabel?: string;
	renderResource?: (booking: Booking) => ReactNode;
	statusLabels?: Partial<Record<BookingStatus, string>>;
	/** The resource type's configured fields, to show the booking's own `customFieldValues`. */
	fields?: FieldDefinition[];
	referenceOptions?: Record<string, ReferenceOption[]>;
	/** Omit an action to hide it entirely, regardless of what the booking's status would otherwise allow. */
	onCheckIn?: () => void;
	onCancel?: () => void;
	onApprove?: () => void;
	onReject?: (reason: string) => void;
	isCheckingIn?: boolean;
	isCancelling?: boolean;
	isApproving?: boolean;
	isRejecting?: boolean;
	/** Defaults to `new Date()` — override in a story/test to pin the check-in window. */
	now?: Date;
	/** A denial or error banner from the caller's own mutation. */
	error?: ReactNode;
	checkInLabel?: string;
	cancelLabel?: string;
	approveLabel?: string;
	rejectLabel?: string;
	rejectReasonPlaceholder?: string;
}

/** Read-only view of a booking, clicked from the grid or month overview — with status-appropriate actions. */
export function BookingDetailsPanel({
	booking,
	resourceLabel,
	renderResource,
	statusLabels,
	fields = [],
	referenceOptions,
	onCheckIn,
	onCancel,
	onApprove,
	onReject,
	isCheckingIn = false,
	isCancelling = false,
	isApproving = false,
	isRejecting = false,
	now = new Date(),
	error,
	checkInLabel = 'Check in',
	cancelLabel = 'Cancel booking',
	approveLabel = 'Approve',
	rejectLabel = 'Reject',
	rejectReasonPlaceholder = 'Reason shown to the member',
}: BookingDetailsPanelProps) {
	const [isRejectOpen, setIsRejectOpen] = useState(false);
	const [reason, setReason] = useState('');

	const canCheckIn = !!onCheckIn && isCheckInOpen(booking, now);
	const canCancel =
		!!onCancel &&
		(booking.status === 'awaiting_payment' ||
			booking.status === 'pending_approval' ||
			booking.status === 'confirmed');
	const canApprove = !!onApprove && booking.status === 'pending_approval';
	const canReject = !!onReject && booking.status === 'pending_approval';

	const handleReject = () => {
		onReject?.(reason);
	};

	return (
		<div className='flex flex-col gap-4'>
			<div>
				<h3 className='text-lg font-medium'>
					{renderResource ? renderResource(booking) : (resourceLabel ?? 'Resource')}
				</h3>
				<p className='text-muted-foreground text-sm'>
					{formatTimeRange(booking.start, booking.end)}
				</p>
			</div>

			<div>
				<BookingStatusBadge labels={statusLabels} status={booking.status} />
			</div>

			{fields.length > 0 ? (
				<div className='flex flex-col gap-1.5'>
					{fields.map((field) => (
						<FieldValueView
							field={field}
							key={field.key}
							referenceOptions={referenceOptions}
							value={booking.customFieldValues[field.key]}
						/>
					))}
				</div>
			) : null}

			{error}

			<div className='flex flex-col gap-2'>
				{canApprove ? (
					<Button disabled={isApproving} onClick={onApprove} type='button'>
						{approveLabel}
					</Button>
				) : null}
				{canReject ? (
					<Button
						disabled={isRejecting}
						onClick={() => setIsRejectOpen(true)}
						type='button'
						variant='ghost'
					>
						{rejectLabel}
					</Button>
				) : null}
				{canCheckIn ? (
					<Button disabled={isCheckingIn} onClick={onCheckIn} type='button'>
						<Icon name='LogIn' />
						{checkInLabel}
					</Button>
				) : null}
				{canCancel ? (
					<Button disabled={isCancelling} onClick={onCancel} type='button' variant='destructive'>
						<Icon name='Ban' />
						{cancelLabel}
					</Button>
				) : null}
			</div>

			<ConfirmationModal
				cancelLabel='Cancel'
				confirmDisabled={!reason.trim()}
				confirmLabel={rejectLabel}
				dangerous
				isConfirming={isRejecting}
				onConfirm={handleReject}
				onOpenChange={setIsRejectOpen}
				open={isRejectOpen}
				title='Reject booking'
			>
				<ClearableInput
					clearLabel='Clear'
					onChange={(event) => setReason(event.target.value)}
					onClear={() => setReason('')}
					placeholder={rejectReasonPlaceholder}
					value={reason}
				/>
			</ConfirmationModal>
		</div>
	);
}
