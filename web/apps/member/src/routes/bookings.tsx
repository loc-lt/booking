import { createFileRoute } from '@tanstack/react-router';
import { MyBookingsPage } from '@/features/bookings';

export const Route = createFileRoute('/bookings')({
	component: MyBookingsPage,
});
