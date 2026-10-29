import type { Actor, BookingHistoryEntry, BookingStatus } from '@booking-core/api-client';
import type { ReactNode } from 'react';
import { BookingStatusBadge } from './BookingStatusBadge';
import { formatDateTime } from './formatDateTime';

function defaultRenderActor(actor: Actor): ReactNode {
	return actor.type === 'system' ? 'System' : 'Member';
}

export interface BookingTimelineProps {
	history: BookingHistoryEntry[];
	/** Override one or more default status labels, e.g. to match a tenant's renamed statuses. */
	labels?: Partial<Record<BookingStatus, string>>;
	/** Defaults to "Member" / "System"; override to resolve an actor's id to a real name. */
	renderActor?: (actor: Actor) => ReactNode;
	/**
	 * The contract doesn't carry a reason on history entries yet — pass this to surface one
	 * from elsewhere (e.g. a separate rejection reason) without waiting on that field.
	 */
	getReason?: (entry: BookingHistoryEntry, index: number) => ReactNode;
	emptyState?: ReactNode;
}

export function BookingTimeline({
	history,
	labels,
	renderActor = defaultRenderActor,
	getReason,
	emptyState = <p className='text-muted-foreground text-sm'>No history yet.</p>,
}: BookingTimelineProps) {
	if (history.length === 0) {
		return <>{emptyState}</>;
	}

	return (
		<ol className='flex flex-col gap-4'>
			{history.map((entry, index) => {
				const reason = getReason?.(entry, index);
				return (
					<li
						key={`${entry.fromStatus ?? 'start'}-${entry.toStatus}-${entry.occurredAt}`}
						className='border-border flex flex-col gap-1 border-l-2 pl-4'
					>
						<div className='flex flex-wrap items-center gap-2'>
							{entry.fromStatus && (
								<>
									<BookingStatusBadge status={entry.fromStatus} labels={labels} />
									<span className='text-muted-foreground text-sm'>→</span>
								</>
							)}
							<BookingStatusBadge status={entry.toStatus} labels={labels} />
						</div>
						<p className='text-muted-foreground text-sm'>
							{formatDateTime(entry.occurredAt)} · {renderActor(entry.actor)}
						</p>
						{reason && <p className='text-sm'>{reason}</p>}
					</li>
				);
			})}
		</ol>
	);
}
