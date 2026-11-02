import { Boxes, CalendarClock, CalendarDays, ClipboardCheck } from 'lucide-react';
import type { ComponentType } from 'react';

export interface NavItem {
	to: '/resource-types' | '/approvals' | '/bookings' | '/booking-calendar';
	label: string;
	icon: ComponentType<{ className?: string }>;
}

export const NAV_ITEMS: NavItem[] = [
	{ icon: Boxes, label: 'Resource types', to: '/resource-types' },
	{ icon: ClipboardCheck, label: 'Approvals', to: '/approvals' },
	{ icon: CalendarDays, label: 'Bookings', to: '/bookings' },
	{ icon: CalendarClock, label: 'Calendar', to: '/booking-calendar' },
];
