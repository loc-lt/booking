import { createFileRoute } from '@tanstack/react-router';
import { BookingConfirmationPage } from '@/features/bookings';

export const Route = createFileRoute('/bookings_/$bookingId')({
	component: RouteComponent,
});

function RouteComponent() {
	const { bookingId } = Route.useParams();
	return <BookingConfirmationPage bookingId={bookingId} />;
}
