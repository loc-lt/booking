import {
	ApiError,
	type Booking,
	getListBookingsQueryKey,
	useApproveBooking,
	useCancelBooking,
	useCheckInBooking,
	useCreateBooking,
	useRejectBooking,
} from '@booking-core/api-client';
import {
	BookingCreatePanel,
	BookingDetailsPanel,
	BookingMonthGrid,
	BookingTimeGrid,
	CalendarToolbar,
	type CalendarViewMode,
	getVisibleDays,
	navigateCalendar,
	ResourceSelect,
	type TimeRange,
} from '@booking-core/booking-ui';
import { Calendar, Card, CardContent, CardHeader, Icon, Skeleton } from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { useBookingCalendarData } from './use-booking-calendar-data';

type Panel = { mode: 'create'; range: TimeRange } | { mode: 'details'; booking: Booking } | null;

function toDateKey(date: Date): string {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function toLocalDate(date: string): Date {
	const [year, month, day] = date.split('-').map(Number);
	return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1);
}

function errorCode(error: unknown): string {
	return error instanceof ApiError ? error.code : 'UNKNOWN_ERROR';
}

/** Operator calendar — pick a resource, browse its bookings by Day/Week/Month, and book a new slot by dragging on the grid. */
export function BookingCalendarPage() {
	const [selectedResourceId, setSelectedResourceId] = useState<string>();
	const [viewMode, setViewMode] = useState<CalendarViewMode>('week');
	const [referenceDate, setReferenceDate] = useState(() => toDateKey(new Date()));
	const [panel, setPanel] = useState<Panel>(null);
	// The grid's highlight tracks this separately from `panel.range` (which only
	// seeds the create panel once, on a fresh drag) so adjusting the date/time
	// fields there updates the highlight live without resetting the panel.
	const [highlightRange, setHighlightRange] = useState<TimeRange | null>(null);
	const [createValues, setCreateValues] = useState<Record<string, unknown>>({});

	const { bookingsByDay, fields, isLoading, resources, selectedResource } = useBookingCalendarData(
		selectedResourceId,
		referenceDate,
		viewMode,
	);

	const queryClient = useQueryClient();
	const createBooking = useCreateBooking();
	const cancelBooking = useCancelBooking();
	const checkInBooking = useCheckInBooking();
	const approveBooking = useApproveBooking();
	const rejectBooking = useRejectBooking();

	// Pick the first resource once the list loads, if nothing's selected yet.
	useEffect(() => {
		if (!selectedResourceId && resources.length > 0) {
			setSelectedResourceId(resources[0]?.id);
		}
	}, [resources, selectedResourceId]);

	const visibleDays = getVisibleDays(referenceDate, viewMode);

	// Invalidates every cached bookings list, not just the one backing the
	// current view — Day/Week and Month each query a different date range
	// (see bookingCalendarRange.ts), so a plain refetch of the active query
	// would leave the others' cached pages stale until their own staleTime
	// (app-kit's queryClient.ts) elapses or the page is reloaded.
	const invalidateBookings = useCallback(() => {
		queryClient.invalidateQueries({ queryKey: getListBookingsQueryKey() });
	}, [queryClient]);

	const handleResourceChange = (resourceId: string) => {
		setSelectedResourceId(resourceId);
		setPanel(null);
		setHighlightRange(null);
	};

	const handleViewModeChange = (mode: CalendarViewMode) => {
		setViewMode(mode);
		setPanel(null);
		setHighlightRange(null);
	};

	// Clicking a date in the Month grid drills into that single day, so the
	// user lands straight on a focused Day-view grid to drag a booking on —
	// same reasoning as clicking a date number in Google Calendar/Outlook.
	const handleSelectDay = (day: string) => {
		setViewMode('day');
		setReferenceDate(day);
		setPanel(null);
		setHighlightRange(null);
	};

	const handleClearPanel = useCallback(() => {
		setPanel(null);
		setHighlightRange(null);
		setCreateValues({});
	}, []);

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

	const handleNavigate = (direction: 1 | -1) => {
		setReferenceDate((current) => navigateCalendar(current, viewMode, direction));
	};

	const handleToday = () => setReferenceDate(toDateKey(new Date()));

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
					handleClearPanel();
					invalidateBookings();
				},
			},
		);
	};

	const handleCheckIn = (booking: Booking) => {
		checkInBooking.mutate(
			{ bookingId: booking.id },
			{
				onSuccess: (updated) => {
					setPanel({ mode: 'details', booking: updated });
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
					setPanel({ mode: 'details', booking: updated });
					invalidateBookings();
				},
			},
		);
	};

	const handleApprove = (booking: Booking) => {
		approveBooking.mutate(
			{ bookingId: booking.id },
			{
				onSuccess: (updated) => {
					setPanel({ mode: 'details', booking: updated });
					invalidateBookings();
				},
			},
		);
	};

	const handleReject = (booking: Booking, reason: string) => {
		rejectBooking.mutate(
			{ bookingId: booking.id, data: { reason } },
			{
				onSuccess: (updated) => {
					setPanel({ mode: 'details', booking: updated });
					invalidateBookings();
				},
			},
		);
	};

	const toolbarTitle = toLocalDate(referenceDate).toLocaleDateString(undefined, {
		month: 'long',
		year: 'numeric',
	});

	const detailsError =
		cancelBooking.error || checkInBooking.error || approveBooking.error || rejectBooking.error ? (
			<p className='text-destructive text-sm'>
				Couldn't update the booking (
				{errorCode(
					cancelBooking.error ??
						checkInBooking.error ??
						approveBooking.error ??
						rejectBooking.error,
				)}
				).
			</p>
		) : undefined;

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
								<p className='text-muted-foreground text-sm'>
									Add a resource under Resource types to start booking it.
								</p>
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
											Couldn't book this slot ({errorCode(createBooking.error)}).
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
								isApproving={approveBooking.isPending}
								isCancelling={cancelBooking.isPending}
								isCheckingIn={checkInBooking.isPending}
								isRejecting={rejectBooking.isPending}
								onApprove={() => handleApprove(panel.booking)}
								onCancel={() => handleCancel(panel.booking)}
								onCheckIn={() => handleCheckIn(panel.booking)}
								onReject={(reason) => handleReject(panel.booking, reason)}
								resourceLabel={selectedResource?.label}
							/>
						) : (
							<div className='flex flex-col items-center gap-2 rounded-xl border border-dashed px-6 py-16 text-center'>
								<Icon className='text-muted-foreground size-8' name='CalendarPlus' />
								<p className='text-muted-foreground text-sm'>
									Drag on the calendar to book a time, or click an existing booking to see its
									details.
								</p>
							</div>
						)}
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
