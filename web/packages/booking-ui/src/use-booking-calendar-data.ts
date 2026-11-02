import {
	getGetResourceTypeQueryKey,
	getListBookingsQueryKey,
	useGetResourceType,
	useListBookings,
	useListResources,
} from '@booking-core/api-client';
import { useMemo } from 'react';
import { getQueryRange, groupBookingsByDay } from './booking-calendar-range';
import { isBlockingBooking } from './booking-occupancy';
import type { CalendarViewMode } from './calendar-navigation';

export function useBookingCalendarData(
	resourceId: string | undefined,
	referenceDate: string,
	viewMode: CalendarViewMode,
) {
	const resourcesQuery = useListResources();
	const resources = resourcesQuery.data?.data ?? [];
	const selectedResource = resources.find((resource) => resource.id === resourceId);

	const resourceTypeId = selectedResource?.resourceTypeId ?? '';
	const resourceTypeQuery = useGetResourceType(resourceTypeId, {
		query: { enabled: !!selectedResource, queryKey: getGetResourceTypeQueryKey(resourceTypeId) },
	});
	const fields = resourceTypeQuery.data?.fields ?? [];

	const { from, to } = getQueryRange(referenceDate, viewMode);
	const bookingsParams = { resourceId, from, to };
	const bookingsQuery = useListBookings(bookingsParams, {
		query: { enabled: !!resourceId, queryKey: getListBookingsQueryKey(bookingsParams) },
	});
	// Cancelled/rejected/expired/no-show bookings left their slot free — a new
	// booking can occupy the same range, so showing both would overlap on the
	// grid. Only bookings still holding their slot are worth rendering here.
	const bookingsByDay = useMemo(
		() => groupBookingsByDay((bookingsQuery.data?.data ?? []).filter(isBlockingBooking)),
		[bookingsQuery.data],
	);

	return {
		bookingsByDay,
		bookingsQuery,
		fields,
		isLoading: resourcesQuery.isPending || (!!resourceId && bookingsQuery.isPending),
		resources,
		resourcesQuery,
		selectedResource,
	};
}
