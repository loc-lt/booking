import { useEffect, useState } from 'react';
import {
	type CalendarViewMode,
	getVisibleDays,
	navigateCalendar,
	toDateKey,
	toLocalDate,
} from './calendar-navigation';
import { useBookingCalendarData } from './use-booking-calendar-data';

export interface UseBookingCalendarNavigationOptions {
	/** Fired on every resource change, view-mode change, or Month-grid day drill-in — clear any open selection/panel here. */
	onNavigate?: () => void;
}

/**
 * The resource/date/view-mode state and navigation behind every booking
 * calendar screen (console's and member's) and the data it drives — the
 * console/member pages differ only in what they let you *do* with a
 * selected booking or range, not in how you get to one.
 */
export function useBookingCalendarNavigation(options: UseBookingCalendarNavigationOptions = {}) {
	const { onNavigate } = options;
	const [selectedResourceId, setSelectedResourceId] = useState<string>();
	const [viewMode, setViewMode] = useState<CalendarViewMode>('week');
	const [referenceDate, setReferenceDate] = useState(() => toDateKey(new Date()));

	const data = useBookingCalendarData(selectedResourceId, referenceDate, viewMode);
	const { resources } = data;

	// Pick the first resource once the list loads, if nothing's selected yet.
	useEffect(() => {
		if (!selectedResourceId && resources.length > 0) {
			setSelectedResourceId(resources[0]?.id);
		}
	}, [resources, selectedResourceId]);

	const visibleDays = getVisibleDays(referenceDate, viewMode);
	const toolbarTitle = toLocalDate(referenceDate).toLocaleDateString(undefined, {
		month: 'long',
		year: 'numeric',
	});

	const handleResourceChange = (resourceId: string) => {
		setSelectedResourceId(resourceId);
		onNavigate?.();
	};

	const handleViewModeChange = (mode: CalendarViewMode) => {
		setViewMode(mode);
		onNavigate?.();
	};

	// Clicking a date in the Month grid drills into that single day, so the
	// user lands straight on a focused Day-view grid — same reasoning as
	// clicking a date number in Google Calendar/Outlook.
	const handleSelectDay = (day: string) => {
		setViewMode('day');
		setReferenceDate(day);
		onNavigate?.();
	};

	const handleNavigate = (direction: 1 | -1) => {
		setReferenceDate((current) => navigateCalendar(current, viewMode, direction));
	};

	const handleToday = () => setReferenceDate(toDateKey(new Date()));

	return {
		...data,
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
	};
}
