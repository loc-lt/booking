import type { ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { DataTableFilters } from './data-table-filters';
import type { DataTableFilterField, FilterValues } from './types';

// Default 12-column responsive grid shared by every table filter header. Headers
// place fields with `lg:col-span-*`, so they all expect this same container.
const DEFAULT_FILTER_GRID_CLASS = 'grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-12';

export type DataTableFilterCardLabels = {
	/** Defaults to `"Apply"`. */
	apply?: string;
	/** Defaults to `"Clear"`. */
	clear?: string;
	/** Defaults to `"Reset"`. */
	reset?: string;
	/** Defaults to `"Search"`. */
	submit?: string;
};

type Props<TFilters extends FilterValues> = {
	fields: readonly DataTableFilterField<TFilters>[];
	gridClassName?: string;
	labels?: DataTableFilterCardLabels;
	onReset: () => void;
	onSubmit: () => void;
	onValueChange: <TName extends keyof TFilters & string>(
		name: TName,
		value: TFilters[TName],
	) => void;
	title: ReactNode;
	values: TFilters;
};

export function DataTableFilterCard<TFilters extends FilterValues>({
	fields,
	gridClassName = DEFAULT_FILTER_GRID_CLASS,
	labels = {},
	onReset,
	onSubmit,
	onValueChange,
	title,
	values,
}: Props<TFilters>) {
	return (
		<Card>
			<CardHeader className='border-b'>
				<CardTitle>{title}</CardTitle>
			</CardHeader>
			<CardContent>
				<DataTableFilters
					applyLabel={labels.apply ?? 'Apply'}
					clearLabel={labels.clear ?? 'Clear'}
					fields={fields}
					gridClassName={gridClassName}
					onReset={onReset}
					onSubmit={onSubmit}
					onValueChange={onValueChange}
					resetLabel={labels.reset ?? 'Reset'}
					submitLabel={labels.submit ?? 'Search'}
					values={values}
				/>
			</CardContent>
		</Card>
	);
}
