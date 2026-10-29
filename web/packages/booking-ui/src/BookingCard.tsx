import type { Booking, BookingStatus } from '@booking-core/api-client';
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@booking-core/ui';
import type { ReactNode } from 'react';
import { BookingStatusBadge } from './BookingStatusBadge';
import { formatTimeRange } from './formatDateTime';

export interface BookingCardProps {
	booking: Booking;
	/** Shown as the title; falls back to a generic placeholder when omitted. */
	resourceLabel?: string;
	/** Full control over the title content, e.g. to link to the resource or add a thumbnail. */
	renderResource?: (booking: Booking) => ReactNode;
	/** Override one or more default status labels, e.g. to match a tenant's renamed statuses. */
	statusLabels?: Partial<Record<BookingStatus, string>>;
	/** Rendered in the card's action slot, e.g. "Cancel" or "Check in" buttons owned by the app. */
	actions?: ReactNode;
	onClick?: () => void;
}

export function BookingCard({
	booking,
	resourceLabel,
	renderResource,
	statusLabels,
	actions,
	onClick,
}: BookingCardProps) {
	return (
		<Card onClick={onClick} className={onClick ? 'cursor-pointer' : undefined}>
			<CardHeader>
				<CardTitle>
					{renderResource ? renderResource(booking) : (resourceLabel ?? 'Resource')}
				</CardTitle>
				{actions && <CardAction>{actions}</CardAction>}
			</CardHeader>
			<CardContent className='flex flex-col gap-2'>
				<p className='text-muted-foreground text-sm'>
					{formatTimeRange(booking.start, booking.end)}
				</p>
				<BookingStatusBadge status={booking.status} labels={statusLabels} />
			</CardContent>
		</Card>
	);
}
