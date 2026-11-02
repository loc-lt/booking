import { Boxes, CalendarDays, ClipboardCheck } from 'lucide-react';
import type { ComponentType } from 'react';

export interface NavItem {
	to: '/resource-types' | '/approvals' | '/bookings';
	label: string;
	icon: ComponentType<{ className?: string }>;
}

export const NAV_ITEMS: NavItem[] = [
	{ icon: Boxes, label: 'Resource types', to: '/resource-types' },
	{ icon: ClipboardCheck, label: 'Approvals', to: '/approvals' },
	{ icon: CalendarDays, label: 'Bookings', to: '/bookings' },
];
