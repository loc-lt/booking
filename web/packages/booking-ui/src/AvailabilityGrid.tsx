import type { AvailabilitySlot } from '@booking-core/api-client';
import { Button } from '@booking-core/ui';
import type { ReactNode } from 'react';
import { formatTime } from './formatDateTime';

function defaultIsSlotDisabled(slot: AvailabilitySlot): boolean {
	return slot.resourceIds.length === 0;
}

function isSameSlot(a: AvailabilitySlot, b: AvailabilitySlot): boolean {
	return a.start === b.start && a.end === b.end;
}

export interface AvailabilityGridProps {
	slots: AvailabilitySlot[];
	selectedSlot?: AvailabilitySlot;
	onSelectSlot?: (slot: AvailabilitySlot) => void;
	/** Defaults to disabling a slot with no resources still free. */
	isSlotDisabled?: (slot: AvailabilitySlot) => boolean;
	/** Full control over one slot's rendering, e.g. to show remaining capacity. */
	renderSlot?: (
		slot: AvailabilitySlot,
		state: { selected: boolean; disabled: boolean },
	) => ReactNode;
	emptyState?: ReactNode;
}

export function AvailabilityGrid({
	slots,
	selectedSlot,
	onSelectSlot,
	isSlotDisabled = defaultIsSlotDisabled,
	renderSlot,
	emptyState = <p className='text-muted-foreground text-sm'>No slots available.</p>,
}: AvailabilityGridProps) {
	if (slots.length === 0) {
		return <>{emptyState}</>;
	}

	return (
		<div className='grid grid-cols-3 gap-2 sm:grid-cols-4'>
			{slots.map((slot) => {
				const selected = selectedSlot != null && isSameSlot(slot, selectedSlot);
				const disabled = isSlotDisabled(slot);
				const key = `${slot.start}-${slot.end}`;

				if (renderSlot) {
					return <div key={key}>{renderSlot(slot, { selected, disabled })}</div>;
				}

				return (
					<Button
						key={key}
						type='button'
						variant={selected ? 'default' : 'outline'}
						disabled={disabled}
						onClick={() => onSelectSlot?.(slot)}
					>
						{formatTime(slot.start)}
					</Button>
				);
			})}
		</div>
	);
}
