import { type BookingStatus, BookingStatus as Status } from '@booking-core/api-client';
import { Badge, type badgeVariants } from '@booking-core/ui';

type BadgeVariant = NonNullable<Parameters<typeof badgeVariants>[0]>['variant'];

/** Generic, tenant-overridable copy — never bake a product's wording in here. */
export const BOOKING_STATUS_LABELS: Record<BookingStatus, string> = {
	[Status.awaiting_payment]: 'Awaiting payment',
	[Status.pending_approval]: 'Pending approval',
	[Status.confirmed]: 'Confirmed',
	[Status.checked_in]: 'Checked in',
	[Status.completed]: 'Completed',
	[Status.expired]: 'Expired',
	[Status.rejected]: 'Rejected',
	[Status.cancelled]: 'Cancelled',
	[Status.no_show]: 'No show',
};

const STATUS_VARIANTS: Record<BookingStatus, BadgeVariant> = {
	[Status.awaiting_payment]: 'secondary',
	[Status.pending_approval]: 'secondary',
	[Status.confirmed]: 'default',
	[Status.checked_in]: 'default',
	[Status.completed]: 'outline',
	[Status.expired]: 'destructive',
	[Status.rejected]: 'destructive',
	[Status.cancelled]: 'outline',
	[Status.no_show]: 'destructive',
};

export interface BookingStatusBadgeProps {
	status: BookingStatus;
	/** Override one or more default labels, e.g. to match a tenant's renamed statuses. */
	labels?: Partial<Record<BookingStatus, string>>;
	className?: string;
}

export function BookingStatusBadge({ status, labels, className }: BookingStatusBadgeProps) {
	return (
		<Badge variant={STATUS_VARIANTS[status]} className={className}>
			{labels?.[status] ?? BOOKING_STATUS_LABELS[status]}
		</Badge>
	);
}
