import { createFileRoute } from '@tanstack/react-router';
import { BookingCalendarPage } from '@/features/booking-calendar';

export const Route = createFileRoute('/booking-calendar')({
	component: BookingCalendarPage,
});
