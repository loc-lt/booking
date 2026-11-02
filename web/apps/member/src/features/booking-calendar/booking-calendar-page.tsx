import {
	type Booking,
	getListBookingsQueryKey,
	useCancelBooking,
	useCreateBooking,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import {
	BookingCreatePanel,
	BookingDetailsPanel,
	BookingMonthGrid,
	BookingTimeGrid,
	CalendarToolbar,
	getErrorCode,
	ResourceSelect,
	type TimeRange,
	toDateKey,
	toLocalDate,
	useBookingCalendarNavigation,
} from '@booking-core/booking-ui';
import { Calendar, Card, CardContent, CardHeader, Icon, Skeleton } from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { auth } from '@/auth';

type Panel = { mode: 'create'; range: TimeRange } | { mode: 'details'; booking: Booking } | null;

/** Member calendar — pick a resource, see every booking on it by Day/Week/Month, book a free slot by dragging on the grid, and cancel a booking of your own. */
export function BookingCalendarPage() {
	const [panel, setPanel] = useState<Panel>(null);
	// The grid's highlight tracks this separately from `panel.range` (which only
	// seeds the create panel once, on a fresh drag) so adjusting the date/time
	// fields there updates the highlight live without resetting the panel.
	const [highlightRange, setHighlightRange] = useState<TimeRange | null>(null);
	const [createValues, setCreateValues] = useState<Record<string, unknown>>({});

	// Navigating away (resource/view-mode/day change) only drops the open
	// panel and highlight — unlike a successful submit, it leaves any
	// in-progress custom-field values alone in case the drag was accidental.
	const clearSelection = useCallback(() => {
		setPanel(null);
		setHighlightRange(null);
	}, []);

	const handleClearPanel = useCallback(() => {
		clearSelection();
		setCreateValues({});
	}, [clearSelection]);

	const {
		bookingsByDay,
		fields,
		isLoading,
		resources,
		selectedResource,
		selectedResourceId,
		viewMode,
		referenceDate,
		setReferenceDate,
		visibleDays,
		toolbarTitle,
		handleResourceChange,
		handleViewModeChange,
		handleSelectDay,
		handleNavigate,
		handleToday,
	} = useBookingCalendarNavigation({ onNavigate: clearSelection });

	const queryClient = useQueryClient();
	const createBooking = useCreateBooking();
	const cancelBooking = useCancelBooking();

	useEffect(() => {
		trackEvent('booking_calendar_viewed');
	}, []);

	// Invalidates every cached bookings list, not just the one backing the
	// current view — Day/Week and Month each query a different date range, so
	// a plain refetch of the active query would leave the others' cached pages
	// stale until their own staleTime (app-kit's queryClient.ts) elapses.
	const invalidateBookings = useCallback(() => {
		queryClient.invalidateQueries({ queryKey: getListBookingsQueryKey() });
	}, [queryClient]);

	const handleSelectRange = (range: TimeRange) => {
		setPanel({ mode: 'create', range });
		setHighlightRange(range);
	};

	const handleSelectBooking = (booking: Booking) => {
		setPanel({ mode: 'details', booking });
		setHighlightRange(null);
	};

	const handleRangeChange = useCallback((range: TimeRange) => {
		setHighlightRange(range);
	}, []);

	const handleCreateSubmit = (range: TimeRange) => {
		if (!selectedResourceId) return;

		createBooking.mutate(
			{
				data: {
					resourceId: selectedResourceId,
					start: range.start,
					end: range.end,
					customFieldValues: createValues,
				},
			},
			{
				onSuccess: () => {
					const durationMinutes =
						(new Date(range.end).getTime() - new Date(range.start).getTime()) / 60_000;
					trackEvent('booking_submitted', {
						resourceTypeId: selectedResource?.resourceTypeId,
						durationMinutes,
					});
					handleClearPanel();
					invalidateBookings();
				},
			},
		);
	};

	const handleCancel = (booking: Booking) => {
		cancelBooking.mutate(
			{ bookingId: booking.id },
			{
				onSuccess: (updated) => {
					trackEvent('booking_cancelled', { resourceTypeId: updated.resourceTypeId });
					setPanel({ mode: 'details', booking: updated });
					invalidateBookings();
				},
			},
		);
	};

	const detailsError = cancelBooking.error ? (
		<p className='text-destructive text-sm'>
			Couldn't update the booking ({getErrorCode(cancelBooking.error)}).
		</p>
	) : undefined;

	const isOwnBooking = (booking: Booking) => booking.memberId === auth.currentMemberId();

	return (
		<div className='flex flex-col gap-4 p-6 lg:h-[calc(100vh-3rem)] lg:flex-row'>
			<div className='flex w-full shrink-0 flex-col gap-4 lg:w-56'>
				<ResourceSelect
					disabled={resources.length === 0}
					onValueChange={handleResourceChange}
					placeholder='Select a resource'
					resources={resources}
					value={selectedResourceId}
				/>

				<Card>
					<CardContent className='px-2'>
						<Calendar
							mode='single'
							month={toLocalDate(referenceDate)}
							onMonthChange={(date) => setReferenceDate(toDateKey(date))}
							onSelect={(date) => date && setReferenceDate(toDateKey(date))}
							selected={toLocalDate(referenceDate)}
						/>
					</CardContent>
				</Card>
			</div>

			<div className='flex min-h-0 min-w-0 flex-1 flex-col'>
				<Card className='min-h-0 flex-1'>
					<CardHeader className='shrink-0'>
						<CalendarToolbar
							onNext={() => handleNavigate(1)}
							onPrevious={() => handleNavigate(-1)}
							onToday={handleToday}
							onViewModeChange={handleViewModeChange}
							title={toolbarTitle}
							viewMode={viewMode}
						/>
					</CardHeader>
					<CardContent className='flex min-h-0 flex-1 flex-col'>
						{isLoading ? (
							<Skeleton className='h-full w-full' />
						) : resources.length === 0 ? (
							<div className='flex h-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed text-center'>
								<Icon className='text-muted-foreground size-8' name='DoorClosed' />
								<p className='font-medium'>No resources yet</p>
								<p className='text-muted-foreground text-sm'>Check back once one's set up.</p>
							</div>
						) : viewMode === 'month' ? (
							<BookingMonthGrid
								bookingsByDay={bookingsByDay}
								onNavigateMonth={handleNavigate}
								onSelectBooking={handleSelectBooking}
								onSelectDay={handleSelectDay}
								referenceDate={referenceDate}
							/>
						) : (
							<BookingTimeGrid
								bookingsByDay={bookingsByDay}
								days={visibleDays}
								onSelectBooking={handleSelectBooking}
								onSelectRange={handleSelectRange}
								selectedBookingId={panel?.mode === 'details' ? panel.booking.id : undefined}
								selectedRange={highlightRange}
							/>
						)}
					</CardContent>
				</Card>
			</div>

			<div className='w-full shrink-0 lg:w-80'>
				<Card>
					<CardContent>
						{panel?.mode === 'create' ? (
							<BookingCreatePanel
								bookingsByDay={bookingsByDay}
								error={
									createBooking.error ? (
										<p className='text-destructive text-sm'>
											Couldn't book this slot ({getErrorCode(createBooking.error)}).
										</p>
									) : undefined
								}
								fields={fields}
								initialRange={panel.range}
								isSubmitting={createBooking.isPending}
								onRangeChange={handleRangeChange}
								onSubmit={handleCreateSubmit}
								onValuesChange={setCreateValues}
								values={createValues}
							/>
						) : panel?.mode === 'details' ? (
							<BookingDetailsPanel
								booking={panel.booking}
								error={detailsError}
								fields={fields}
								isCancelling={cancelBooking.isPending}
								onCancel={
									isOwnBooking(panel.booking) ? () => handleCancel(panel.booking) : undefined
								}
								resourceLabel={selectedResource?.label}
							/>
						) : (
							<div className='flex flex-col items-center gap-2 rounded-xl border border-dashed px-6 py-16 text-center'>
								<Icon className='text-muted-foreground size-8' name='CalendarPlus' />
								<p className='text-muted-foreground text-sm'>
									Drag on the calendar to book a time, or click a booking to see its details.
								</p>
							</div>
						)}
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
