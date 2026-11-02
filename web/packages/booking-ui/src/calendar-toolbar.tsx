import {
	Button,
	Icon,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@booking-core/ui';
import type { ReactNode } from 'react';
import type { CalendarViewMode } from './calendar-navigation';

const VIEW_MODES: CalendarViewMode[] = ['day', 'week', 'month'];

export interface CalendarToolbarProps {
	/** The visible range's heading, e.g. "November 2026" — formatting is the caller's call. */
	title: ReactNode;
	onPrevious: () => void;
	onNext: () => void;
	onToday: () => void;
	viewMode: CalendarViewMode;
	onViewModeChange: (viewMode: CalendarViewMode) => void;
	/** Overrides one or more of the default "Day" / "Week" / "Month" labels. */
	viewModeLabels?: Partial<Record<CalendarViewMode, string>>;
	todayLabel?: string;
	previousLabel?: string;
	nextLabel?: string;
}

const DEFAULT_VIEW_MODE_LABELS: Record<CalendarViewMode, string> = {
	day: 'Day',
	week: 'Week',
	month: 'Month',
};

export function CalendarToolbar({
	title,
	onPrevious,
	onNext,
	onToday,
	viewMode,
	onViewModeChange,
	viewModeLabels,
	todayLabel = 'Today',
	previousLabel = 'Previous',
	nextLabel = 'Next',
}: CalendarToolbarProps) {
	return (
		<div className='flex flex-wrap items-center justify-between gap-2'>
			<h2 className='text-xl font-semibold'>{title}</h2>
			<div className='flex items-center gap-2'>
				<Button aria-label={previousLabel} onClick={onPrevious} size='icon' variant='outline'>
					<Icon name='ChevronLeft' />
				</Button>
				<Button onClick={onToday} variant='outline'>
					{todayLabel}
				</Button>
				<Button aria-label={nextLabel} onClick={onNext} size='icon' variant='outline'>
					<Icon name='ChevronRight' />
				</Button>
				<Select
					items={VIEW_MODES.map((mode) => ({
						value: mode,
						label: viewModeLabels?.[mode] ?? DEFAULT_VIEW_MODE_LABELS[mode],
					}))}
					onValueChange={(value) => onViewModeChange(value as CalendarViewMode)}
					value={viewMode}
				>
					<SelectTrigger aria-label='View' className='w-28'>
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{VIEW_MODES.map((mode) => (
							<SelectItem key={mode} value={mode}>
								{viewModeLabels?.[mode] ?? DEFAULT_VIEW_MODE_LABELS[mode]}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
			</div>
		</div>
	);
}
