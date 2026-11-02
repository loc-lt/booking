import type { Booking } from '@booking-core/api-client';
import { Icon } from '@booking-core/ui';
import { cn } from 'cn';
import {
	type PointerEvent,
	type ReactNode,
	useEffect,
	useLayoutEffect,
	useRef,
	useState,
} from 'react';
import type { TimeRange } from './booking-occupancy';
import { isBlockingBooking } from './booking-occupancy';
import { BOOKING_STATUS_LABELS } from './booking-status-badge';
import { bookingStatusTone } from './booking-status-tone';
import { formatTime } from './format-date-time';

/** Left-accent + tint per status tone — an at-a-glance read before the label loads. */
const BOOKING_BLOCK_TONE_CLASSES: Record<ReturnType<typeof bookingStatusTone>, string> = {
	active: 'border-l-primary bg-primary/10',
	pending: 'border-l-muted-foreground/70 border-dashed bg-secondary/60',
	neutral: 'border-l-border bg-muted',
};

export type { TimeRange } from './booking-occupancy';

export interface BookingTimeGridProps {
	/** 'YYYY-MM-DD', length 1 for Day view or 7 for Week view. */
	days: string[];
	bookingsByDay: Map<string, Booking[]>;
	/** Fired when a drag, a resize or a move of the draft range settles. */
	onSelectRange: (range: TimeRange) => void;
	onSelectBooking: (booking: Booking) => void;
	/**
	 * Disables drag-to-select entirely (booking blocks stay clickable) — for a
	 * look-only calendar with no booking affordance.
	 */
	readOnly?: boolean;
	/** The range currently shown in a create panel — stays highlighted (and resizable/movable) until replaced or cleared by the caller. */
	selectedRange?: TimeRange | null;
	selectedBookingId?: string;
	/** Defaults to any non-released status (not cancelled/rejected/expired/no_show). */
	isBlocking?: (booking: Booking) => boolean;
	/** Full control over one booking block's content, e.g. to show a tenant's title field. */
	renderBooking?: (booking: Booking) => ReactNode;
	hourHeightPx?: number;
	snapMinutes?: number;
	minSelectionMinutes?: number;
	moveSelectionLabel?: string;
	resizeStartLabel?: string;
	resizeEndLabel?: string;
}

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);
const DEFAULT_HOUR_HEIGHT_PX = 100;
const DEFAULT_SNAP_MINUTES = 15;
const DEFAULT_MIN_SELECTION_MINUTES = 30;
// Below this, a block isn't tall enough to fit two lines without clipping.
const TWO_LINE_BLOCK_MIN_HEIGHT_PX = 36;
const MINUTES_PER_DAY = 24 * 60;
const NOW_REFRESH_INTERVAL_MS = 60_000;
// Half the resize handle's own height (`h-5` = 20px), so it centers on the block's border.
const RESIZE_HANDLE_HALF_HEIGHT_PX = 10;

function toLocalDate(date: string): Date {
	const [year, month, day] = date.split('-').map(Number);
	return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1);
}

function toDateKey(date: Date): string {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function minutesFromMidnight(iso: string): number {
	const date = new Date(iso);
	return date.getHours() * 60 + date.getMinutes();
}

function combineDateAndMinutes(date: string, minutes: number): string {
	const base = toLocalDate(date);
	base.setMinutes(minutes);
	return base.toISOString();
}

function timeLabel(minutes: number): string {
	const hours = Math.floor(minutes / 60);
	const remainder = minutes % 60;
	return `${String(hours).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

function formatDuration(totalMinutes: number): string {
	return `${Math.floor(totalMinutes / 60)}h ${totalMinutes % 60}m`;
}

function clamp(value: number, min: number, max: number): number {
	return Math.min(Math.max(value, min), max);
}

function snapToStep(minutes: number, step: number): number {
	return Math.round(minutes / step) * step;
}

/**
 * The widest [lower, upper] minute range a drag anchored at `anchorMinutes` is
 * allowed to grow into on this day — bounded by the nearest blocking booking
 * on either side, so a drag can't be extended across one that's already there.
 */
function getDragBounds(
	bookings: Booking[],
	anchorMinutes: number,
	isBlocking: (booking: Booking) => boolean,
): { lower: number; upper: number } {
	let lower = 0;
	let upper = MINUTES_PER_DAY;

	for (const booking of bookings) {
		if (!isBlocking(booking)) continue;

		const start = minutesFromMidnight(booking.start);
		const end = minutesFromMidnight(booking.end);

		if (anchorMinutes > start && anchorMinutes < end) {
			return { lower: anchorMinutes, upper: anchorMinutes };
		}

		if (end <= anchorMinutes) {
			lower = Math.max(lower, end);
		} else if (start >= anchorMinutes) {
			upper = Math.min(upper, start);
		}
	}

	return { lower, upper };
}

/**
 * The valid [lower, upper] range for a fixed-`durationMinutes` block's start
 * time, given it would ideally start at `desiredStart` — like `getDragBounds`,
 * but for moving a whole block rather than resizing one edge of it.
 */
function getMoveBounds(
	bookings: Booking[],
	desiredStart: number,
	durationMinutes: number,
	isBlocking: (booking: Booking) => boolean,
): { lower: number; upper: number } {
	let lower = 0;
	let upper = MINUTES_PER_DAY - durationMinutes;
	const desiredEnd = desiredStart + durationMinutes;

	for (const booking of bookings) {
		if (!isBlocking(booking)) continue;

		const start = minutesFromMidnight(booking.start);
		const end = minutesFromMidnight(booking.end);

		if (end <= desiredStart) {
			lower = Math.max(lower, end);
		} else if (start >= desiredEnd) {
			upper = Math.min(upper, start - durationMinutes);
		} else {
			const before = start - durationMinutes;
			const after = end;
			if (Math.abs(desiredStart - before) <= Math.abs(desiredStart - after)) {
				upper = Math.min(upper, before);
			} else {
				lower = Math.max(lower, after);
			}
		}
	}

	return { lower, upper: Math.max(upper, lower) };
}

/**
 * The latest a moved block starting at `startMinutes` is allowed to end — the
 * start of the next blocking booking below it, or the end of the day.
 */
function getMoveMaxEnd(
	bookings: Booking[],
	startMinutes: number,
	isBlocking: (booking: Booking) => boolean,
): number {
	let maxEnd = MINUTES_PER_DAY;

	for (const booking of bookings) {
		if (!isBlocking(booking)) continue;

		const start = minutesFromMidnight(booking.start);
		if (start > startMinutes) {
			maxEnd = Math.min(maxEnd, start);
		}
	}

	return maxEnd;
}

type Drag = { endMinutes: number; startMinutes: number };
type ResizeEdge = 'end' | 'start';
type ResizeDrag = { edge: ResizeEdge; minutes: number };
// The selected block currently being dragged to a new day/time — `date` and
// `startMinutes` track the live drop target; `durationMinutes` stays fixed for
// the whole gesture. `endMinutes` is normally `startMinutes + durationMinutes`,
// but shrinks to fit a gap between two bookings shorter than its full duration.
type MoveDrag = { date: string; durationMinutes: number; endMinutes: number; startMinutes: number };

function DayColumn({
	bookings,
	date,
	hourHeightPx,
	isBlocking,
	isToday,
	minSelectionMinutes,
	moveDrag,
	moveSelectionLabel,
	onMoveEnd,
	onMoveMove,
	onMoveStart,
	onSelectBooking,
	onSelectRange,
	readOnly,
	renderBooking,
	resizeEndLabel,
	resizeStartLabel,
	selectedBookingId,
	selectedRange,
	snapMinutes,
}: {
	bookings: Booking[];
	date: string;
	hourHeightPx: number;
	isBlocking: (booking: Booking) => boolean;
	isToday: boolean;
	minSelectionMinutes: number;
	moveDrag: MoveDrag | null;
	moveSelectionLabel: string;
	onMoveEnd: (event: PointerEvent<HTMLButtonElement>) => void;
	onMoveMove: (event: PointerEvent<HTMLButtonElement>) => void;
	onMoveStart: (event: PointerEvent<HTMLButtonElement>, date: string) => void;
	onSelectBooking: (booking: Booking) => void;
	onSelectRange: (range: TimeRange) => void;
	readOnly: boolean;
	renderBooking?: (booking: Booking) => ReactNode;
	resizeEndLabel: string;
	resizeStartLabel: string;
	selectedBookingId: string | undefined;
	selectedRange: TimeRange | null;
	snapMinutes: number;
}) {
	const gridHeightPx = hourHeightPx * HOURS.length;
	const containerRef = useRef<HTMLDivElement>(null);
	const [drag, setDrag] = useState<Drag | null>(null);
	const [resizeDrag, setResizeDrag] = useState<ResizeDrag | null>(null);

	const minutesFromPointer = (clientY: number): number => {
		const rect = containerRef.current?.getBoundingClientRect();
		if (!rect) return 0;

		const rawMinutes = ((clientY - rect.top) / hourHeightPx) * 60;
		return clamp(snapToStep(rawMinutes, snapMinutes), 0, MINUTES_PER_DAY);
	};

	const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
		event.currentTarget.setPointerCapture(event.pointerId);
		const minutes = minutesFromPointer(event.clientY);
		setDrag({ endMinutes: minutes, startMinutes: minutes });
	};

	const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
		if (!drag) return;

		const bounds = getDragBounds(bookings, drag.startMinutes, isBlocking);
		const minutes = clamp(minutesFromPointer(event.clientY), bounds.lower, bounds.upper);
		setDrag((current) => current && { ...current, endMinutes: minutes });
	};

	const handlePointerUp = () => {
		if (!drag) return;

		const bounds = getDragBounds(bookings, drag.startMinutes, isBlocking);
		const start = clamp(Math.min(drag.startMinutes, drag.endMinutes), bounds.lower, bounds.upper);
		let end = clamp(Math.max(drag.startMinutes, drag.endMinutes), bounds.lower, bounds.upper);

		if (end - start < minSelectionMinutes) {
			end = Math.min(start + minSelectionMinutes, bounds.upper);
		}

		setDrag(null);

		// No free space at all at this anchor — drop the drag instead of
		// committing a zero-width range the create panel couldn't work with.
		if (end <= start) return;

		onSelectRange({
			start: combineDateAndMinutes(date, start),
			end: combineDateAndMinutes(date, end),
		});
	};

	// While actively dragging, the live drag wins; once released, fall back to
	// the caller's persisted selection (if it's on this day) so the highlight
	// stays put instead of vanishing the instant the pointer lifts.
	const highlight = drag
		? {
				endMinutes: Math.max(drag.startMinutes, drag.endMinutes),
				startMinutes: Math.min(drag.startMinutes, drag.endMinutes),
			}
		: selectedRange && toDateKey(new Date(selectedRange.start)) === date
			? {
					endMinutes:
						resizeDrag?.edge === 'end'
							? resizeDrag.minutes
							: minutesFromMidnight(selectedRange.end),
					startMinutes:
						resizeDrag?.edge === 'start'
							? resizeDrag.minutes
							: minutesFromMidnight(selectedRange.start),
				}
			: null;

	const moveGhost =
		moveDrag && moveDrag.date === date
			? { endMinutes: moveDrag.endMinutes, startMinutes: moveDrag.startMinutes }
			: null;

	const isEditableSelection =
		!drag &&
		!moveDrag &&
		selectedRange !== null &&
		toDateKey(new Date(selectedRange.start)) === date;

	const handleEdgeResizeStart = (edge: ResizeEdge) => (event: PointerEvent<HTMLButtonElement>) => {
		if (!highlight) return;

		event.stopPropagation();
		event.currentTarget.setPointerCapture(event.pointerId);
		setResizeDrag({
			edge,
			minutes: edge === 'start' ? highlight.startMinutes : highlight.endMinutes,
		});
	};

	const handleEdgeResizeMove = (event: PointerEvent<HTMLButtonElement>) => {
		if (!resizeDrag || !highlight) return;

		event.stopPropagation();
		const pointerMinutes = minutesFromPointer(event.clientY);

		if (resizeDrag.edge === 'start') {
			const bounds = getDragBounds(bookings, highlight.endMinutes, isBlocking);
			const minutes = clamp(
				pointerMinutes,
				bounds.lower,
				highlight.endMinutes - minSelectionMinutes,
			);
			setResizeDrag({ edge: 'start', minutes });
		} else {
			const bounds = getDragBounds(bookings, highlight.startMinutes, isBlocking);
			const minutes = clamp(
				pointerMinutes,
				highlight.startMinutes + minSelectionMinutes,
				bounds.upper,
			);
			setResizeDrag({ edge: 'end', minutes });
		}
	};

	const handleEdgeResizeEnd = (event: PointerEvent<HTMLButtonElement>) => {
		if (!resizeDrag || !highlight) return;

		event.stopPropagation();
		setResizeDrag(null);
		onSelectRange({
			start: combineDateAndMinutes(
				date,
				resizeDrag.edge === 'start' ? resizeDrag.minutes : highlight.startMinutes,
			),
			end: combineDateAndMinutes(
				date,
				resizeDrag.edge === 'end' ? resizeDrag.minutes : highlight.endMinutes,
			),
		});
	};

	const blockHeight = highlight
		? Math.max(((highlight.endMinutes - highlight.startMinutes) / 60) * hourHeightPx, 4)
		: 0;
	const moveGhostHeight = moveGhost
		? Math.max(((moveGhost.endMinutes - moveGhost.startMinutes) / 60) * hourHeightPx, 4)
		: 0;

	return (
		<div
			className={cn(
				'relative touch-none border-l select-none',
				isToday ? 'bg-primary/5' : undefined,
			)}
			data-testid={`booking-day-column-${date}`}
			onPointerDown={readOnly ? undefined : handlePointerDown}
			onPointerMove={readOnly ? undefined : handlePointerMove}
			onPointerUp={readOnly ? undefined : handlePointerUp}
			ref={containerRef}
			style={{ height: gridHeightPx }}
		>
			{HOURS.map((hour) => (
				<div className='border-t' key={hour} style={{ height: hourHeightPx }} />
			))}

			{bookings.map((booking) => {
				const top = (minutesFromMidnight(booking.start) / 60) * hourHeightPx;
				const height =
					((minutesFromMidnight(booking.end) - minutesFromMidnight(booking.start)) / 60) *
					hourHeightPx;
				const fitsTwoLines = height >= TWO_LINE_BLOCK_MIN_HEIGHT_PX;

				return (
					<button
						className={cn(
							'absolute inset-x-1 overflow-hidden rounded-md border-l-4 px-2 py-1 text-left text-xs shadow-sm transition-shadow hover:shadow-md',
							BOOKING_BLOCK_TONE_CLASSES[bookingStatusTone(booking.status)],
							booking.id === selectedBookingId ? 'ring-primary ring-2' : 'ring-border/60 ring-1',
						)}
						key={booking.id}
						onClick={() => onSelectBooking(booking)}
						onPointerDown={(event) => event.stopPropagation()}
						style={{ height: Math.max(height, 4), top }}
						type='button'
					>
						{renderBooking ? (
							renderBooking(booking)
						) : fitsTwoLines ? (
							<>
								<span className='text-foreground block truncate leading-tight font-semibold'>
									{formatTime(booking.start)} – {formatTime(booking.end)}
								</span>
								<span className='text-muted-foreground block truncate leading-tight'>
									{BOOKING_STATUS_LABELS[booking.status]}
								</span>
							</>
						) : (
							<span className='text-foreground block truncate font-semibold'>
								{formatTime(booking.start)}
							</span>
						)}
					</button>
				);
			})}

			{highlight ? (
				<button
					aria-label={moveSelectionLabel}
					className={cn(
						'absolute inset-x-1 flex items-center justify-center overflow-hidden rounded-md transition-opacity',
						moveDrag
							? 'pointer-events-none opacity-0'
							: 'bg-primary/25 ring-primary cursor-grab ring-1 active:cursor-grabbing',
					)}
					data-testid='booking-selection-highlight'
					onPointerDown={readOnly || moveDrag ? undefined : (event) => onMoveStart(event, date)}
					onPointerMove={readOnly ? undefined : onMoveMove}
					onPointerUp={readOnly ? undefined : onMoveEnd}
					style={{ height: blockHeight, top: (highlight.startMinutes / 60) * hourHeightPx }}
					type='button'
				>
					<span className='text-primary truncate px-1 text-xs font-medium'>
						{formatDuration(highlight.endMinutes - highlight.startMinutes)}
					</span>
				</button>
			) : null}

			{isEditableSelection && highlight ? (
				<>
					<button
						aria-label={resizeStartLabel}
						className='bg-primary text-primary-foreground absolute left-1/2 flex h-5 w-6 -translate-x-1/2 cursor-ns-resize items-center justify-center rounded'
						data-testid='booking-resize-handle-start'
						onPointerDown={handleEdgeResizeStart('start')}
						onPointerMove={handleEdgeResizeMove}
						onPointerUp={handleEdgeResizeEnd}
						style={{
							top: (highlight.startMinutes / 60) * hourHeightPx - RESIZE_HANDLE_HALF_HEIGHT_PX,
						}}
						type='button'
					>
						<Icon className='size-3' name='GripHorizontal' />
					</button>
					<button
						aria-label={resizeEndLabel}
						className='bg-primary text-primary-foreground absolute left-1/2 flex h-5 w-6 -translate-x-1/2 cursor-ns-resize items-center justify-center rounded'
						data-testid='booking-resize-handle-end'
						onPointerDown={handleEdgeResizeStart('end')}
						onPointerMove={handleEdgeResizeMove}
						onPointerUp={handleEdgeResizeEnd}
						style={{
							top: (highlight.endMinutes / 60) * hourHeightPx - RESIZE_HANDLE_HALF_HEIGHT_PX,
						}}
						type='button'
					>
						<Icon className='size-3' name='GripHorizontal' />
					</button>
				</>
			) : null}

			{moveGhost ? (
				<div
					className='border-primary bg-primary/25 pointer-events-none absolute inset-x-1 flex items-center justify-center overflow-hidden rounded-md border-2 border-dashed'
					data-testid='booking-move-preview'
					style={{ height: moveGhostHeight, top: (moveGhost.startMinutes / 60) * hourHeightPx }}
				>
					<span className='text-primary truncate px-1 text-xs font-medium'>
						{formatDuration(moveGhost.endMinutes - moveGhost.startMinutes)}
					</span>
				</div>
			) : null}
		</div>
	);
}

/** Week/Day drag-to-select time grid — drag on a day column to pick a booking's time range, or drag an already-selected (not yet submitted) block to move it. */
export function BookingTimeGrid({
	days,
	bookingsByDay,
	onSelectRange,
	onSelectBooking,
	readOnly = false,
	selectedRange = null,
	selectedBookingId,
	isBlocking = isBlockingBooking,
	renderBooking,
	hourHeightPx = DEFAULT_HOUR_HEIGHT_PX,
	snapMinutes = DEFAULT_SNAP_MINUTES,
	minSelectionMinutes = DEFAULT_MIN_SELECTION_MINUTES,
	moveSelectionLabel = 'Move selection',
	resizeStartLabel = 'Resize start',
	resizeEndLabel = 'Resize end',
}: BookingTimeGridProps) {
	const [now, setNow] = useState(() => new Date());
	const [moveDrag, setMoveDrag] = useState<MoveDrag | null>(null);
	const scrollContainerRef = useRef<HTMLDivElement>(null);
	const columnsRef = useRef<HTMLDivElement>(null);
	// The pointer's grabbed position relative to the block's start, in minutes
	// — held constant for the whole gesture so the block doesn't jump to
	// re-center under the cursor when the drag begins.
	const moveGrabOffsetRef = useRef(0);

	useEffect(() => {
		const interval = setInterval(() => setNow(new Date()), NOW_REFRESH_INTERVAL_MS);
		return () => clearInterval(interval);
	}, []);

	const today = toDateKey(now);
	const gridTemplateColumns = { gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` };
	const showNowIndicator = days.includes(today);
	const nowTopPx = ((now.getHours() * 60 + now.getMinutes()) / 60) * hourHeightPx;

	// Land on "now" instead of the top of the day — center the current-time
	// line in the scrollable viewport on first render. Deliberately mount-only
	// (empty deps): should scroll into view once, not every time `now` ticks.
	// biome-ignore lint/correctness/useExhaustiveDependencies: see comment above
	useLayoutEffect(() => {
		const container = scrollContainerRef.current;
		if (!showNowIndicator || !container) return;

		const maxScrollTop = container.scrollHeight - container.clientHeight;
		container.scrollTop = clamp(nowTopPx - container.clientHeight / 2, 0, maxScrollTop);
	}, []);

	const minutesFromClientY = (clientY: number): number => {
		const rect = columnsRef.current?.getBoundingClientRect();
		if (!rect) return 0;

		const rawMinutes = ((clientY - rect.top) / hourHeightPx) * 60;
		return clamp(snapToStep(rawMinutes, snapMinutes), 0, MINUTES_PER_DAY);
	};

	const dateFromClientX = (clientX: number): string => {
		const rect = columnsRef.current?.getBoundingClientRect();
		const fallback = days[0] ?? '';
		if (!rect || days.length === 0) return fallback;

		const index = clamp(
			Math.floor(((clientX - rect.left) / rect.width) * days.length),
			0,
			days.length - 1,
		);
		return days[index] ?? fallback;
	};

	const handleMoveStart = (event: PointerEvent<HTMLButtonElement>, date: string) => {
		if (readOnly || !selectedRange || toDateKey(new Date(selectedRange.start)) !== date) return;

		event.stopPropagation();
		event.currentTarget.setPointerCapture(event.pointerId);

		const startMinutes = minutesFromMidnight(selectedRange.start);
		const endMinutes = minutesFromMidnight(selectedRange.end);
		moveGrabOffsetRef.current = minutesFromClientY(event.clientY) - startMinutes;

		setMoveDrag({ date, durationMinutes: endMinutes - startMinutes, endMinutes, startMinutes });
	};

	const handleMoveMove = (event: PointerEvent<HTMLButtonElement>) => {
		if (!moveDrag) return;

		event.stopPropagation();

		const targetDate = dateFromClientX(event.clientX);
		const targetBookings = bookingsByDay.get(targetDate) ?? [];
		const pointerMinutes = minutesFromClientY(event.clientY);
		const desiredStart = pointerMinutes - moveGrabOffsetRef.current;

		const bounds = getMoveBounds(
			targetBookings,
			desiredStart,
			moveDrag.durationMinutes,
			isBlocking,
		);
		const boundedStart = clamp(desiredStart, bounds.lower, Math.max(bounds.upper, bounds.lower));
		const startMinutes = clamp(boundedStart, 0, MINUTES_PER_DAY - moveDrag.durationMinutes);
		const endMinutes = Math.min(
			startMinutes + moveDrag.durationMinutes,
			getMoveMaxEnd(targetBookings, startMinutes, isBlocking),
		);

		setMoveDrag({
			date: targetDate,
			durationMinutes: moveDrag.durationMinutes,
			endMinutes,
			startMinutes,
		});
	};

	const handleMoveEnd = (event: PointerEvent<HTMLButtonElement>) => {
		if (!moveDrag) return;

		event.stopPropagation();
		setMoveDrag(null);

		if (moveDrag.endMinutes - moveDrag.startMinutes < minSelectionMinutes) return;

		onSelectRange({
			start: combineDateAndMinutes(moveDrag.date, moveDrag.startMinutes),
			end: combineDateAndMinutes(moveDrag.date, moveDrag.endMinutes),
		});
	};

	return (
		<div className='flex min-h-0 flex-1 flex-col overflow-x-auto'>
			<div className='flex min-h-0 min-w-[560px] flex-1 flex-col'>
				<div className='flex shrink-0'>
					<div className='w-14 shrink-0' />
					<div className='grid flex-1' style={gridTemplateColumns}>
						{days.map((day) => {
							const isToday = day === today;
							const date = toLocalDate(day);

							return (
								<div
									className={cn(
										'flex items-center justify-center gap-1.5 border-b py-2 text-sm',
										isToday ? 'text-primary' : undefined,
									)}
									key={day}
								>
									<span className='text-muted-foreground'>
										{date.toLocaleDateString(undefined, { weekday: 'short' })}
									</span>
									<span
										className={cn(
											'flex size-6 items-center justify-center rounded-full font-medium',
											isToday ? 'bg-primary text-primary-foreground' : undefined,
										)}
									>
										{date.getDate()}
									</span>
								</div>
							);
						})}
					</div>
				</div>

				<div
					className='no-scrollbar min-h-0 flex-1 overflow-y-auto pt-2'
					data-testid='booking-time-scroll-container'
					ref={scrollContainerRef}
				>
					<div className='relative flex'>
						<div className='w-14 shrink-0'>
							{HOURS.map((hour) => (
								<div className='relative' key={hour} style={{ height: hourHeightPx }}>
									<span className='text-muted-foreground absolute right-2 -translate-y-1/2 text-xs'>
										{timeLabel(hour * 60)}
									</span>
								</div>
							))}
						</div>
						<div className='grid flex-1' ref={columnsRef} style={gridTemplateColumns}>
							{days.map((day) => (
								<DayColumn
									bookings={bookingsByDay.get(day) ?? []}
									date={day}
									hourHeightPx={hourHeightPx}
									isBlocking={isBlocking}
									isToday={day === today}
									key={day}
									minSelectionMinutes={minSelectionMinutes}
									moveDrag={moveDrag}
									moveSelectionLabel={moveSelectionLabel}
									onMoveEnd={handleMoveEnd}
									onMoveMove={handleMoveMove}
									onMoveStart={handleMoveStart}
									onSelectBooking={onSelectBooking}
									onSelectRange={onSelectRange}
									readOnly={readOnly}
									renderBooking={renderBooking}
									resizeEndLabel={resizeEndLabel}
									resizeStartLabel={resizeStartLabel}
									selectedBookingId={selectedBookingId}
									selectedRange={selectedRange}
									snapMinutes={snapMinutes}
								/>
							))}
						</div>

						{showNowIndicator ? (
							<div
								className='pointer-events-none absolute inset-x-0 z-10 flex -translate-y-1/2 items-center'
								data-testid='booking-now-indicator'
								style={{ top: nowTopPx }}
							>
								<div className='flex w-14 shrink-0 justify-end pr-1.5'>
									<span className='rounded bg-red-500 px-1.5 py-0.5 text-[10px] leading-none font-medium text-white'>
										{timeLabel(now.getHours() * 60 + now.getMinutes())}
									</span>
								</div>
								<div className='h-px flex-1 bg-red-500' />
							</div>
						) : null}
					</div>
				</div>
			</div>
		</div>
	);
}
