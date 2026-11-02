import {
	getGetResourceTypeQueryKey,
	getListBookingsQueryKey,
	useGetResourceType,
	useListBookings,
	useListResources,
} from '@booking-core/api-client';
import type { CalendarViewMode } from '@booking-core/booking-ui';
import { useMemo } from 'react';
import { getQueryRange, groupBookingsByDay } from './booking-calendar-range';

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
	const bookingsByDay = useMemo(
		() => groupBookingsByDay(bookingsQuery.data?.data ?? []),
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
