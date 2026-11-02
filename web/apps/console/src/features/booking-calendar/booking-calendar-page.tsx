import {
	type Booking,
	getListBookingsQueryKey,
	useApproveBooking,
	useCancelBooking,
	useCheckInBooking,
	useRejectBooking,
} from '@booking-core/api-client';
import {
	BookingDetailsPanel,
	BookingMonthGrid,
	BookingTimeGrid,
	CalendarToolbar,
	getErrorCode,
	ResourceSelect,
	toDateKey,
	toLocalDate,
	useBookingCalendarNavigation,
} from '@booking-core/booking-ui';
import { Calendar, Card, CardContent, CardHeader, Icon, Skeleton } from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';

/** Operator calendar — pick a resource and browse its bookings by Day/Week/Month; view-only, with cancel, check-in, approve and reject from a booking's details. */
export function BookingCalendarPage() {
	const [selectedBooking, setSelectedBooking] = useState<Booking>();

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
	} = useBookingCalendarNavigation({ onNavigate: () => setSelectedBooking(undefined) });

	const queryClient = useQueryClient();
	const cancelBooking = useCancelBooking();
	const checkInBooking = useCheckInBooking();
	const approveBooking = useApproveBooking();
	const rejectBooking = useRejectBooking();

	// Invalidates every cached bookings list, not just the one backing the
	// current view — Day/Week and Month each query a different date range
	// (see bookingCalendarRange.ts), so a plain refetch of the active query
	// would leave the others' cached pages stale until their own staleTime
	// (app-kit's queryClient.ts) elapses or the page is reloaded.
	const invalidateBookings = useCallback(() => {
		queryClient.invalidateQueries({ queryKey: getListBookingsQueryKey() });
	}, [queryClient]);

	const handleSelectBooking = (booking: Booking) => {
		setSelectedBooking(booking);
	};

	const handleCheckIn = (booking: Booking) => {
		checkInBooking.mutate(
			{ bookingId: booking.id },
			{
				onSuccess: (updated) => {
					setSelectedBooking(updated);
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
					setSelectedBooking(updated);
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
					setSelectedBooking(updated);
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
					setSelectedBooking(updated);
					invalidateBookings();
				},
			},
		);
	};

	const detailsError =
		cancelBooking.error || checkInBooking.error || approveBooking.error || rejectBooking.error ? (
			<p className='text-destructive text-sm'>
				Couldn't update the booking (
				{getErrorCode(
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
								onSelectRange={() => {}}
								readOnly
								selectedBookingId={selectedBooking?.id}
							/>
						)}
					</CardContent>
				</Card>
			</div>

			<div className='w-full shrink-0 lg:w-80'>
				<Card>
					<CardContent>
						{selectedBooking ? (
							<BookingDetailsPanel
								booking={selectedBooking}
								error={detailsError}
								fields={fields}
								isApproving={approveBooking.isPending}
								isCancelling={cancelBooking.isPending}
								isCheckingIn={checkInBooking.isPending}
								isRejecting={rejectBooking.isPending}
								onApprove={() => handleApprove(selectedBooking)}
								onCancel={() => handleCancel(selectedBooking)}
								onCheckIn={() => handleCheckIn(selectedBooking)}
								onReject={(reason) => handleReject(selectedBooking, reason)}
								resourceLabel={selectedResource?.label}
							/>
						) : (
							<div className='flex flex-col items-center gap-2 rounded-xl border border-dashed px-6 py-16 text-center'>
								<Icon className='text-muted-foreground size-8' name='CalendarPlus' />
								<p className='text-muted-foreground text-sm'>
									Click an existing booking to see its details.
								</p>
							</div>
						)}
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
