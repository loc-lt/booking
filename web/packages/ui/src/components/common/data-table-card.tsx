import { type ReactNode, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { DataTable } from './data-table';
import type {
	DataTableColumn,
	DataTablePagination,
	DataTablePaginationState,
	DataTableSort,
	DataTableSortState,
} from './types';

export type DataTableCardLabels = {
	/** Defaults to `"Clear sort"`. */
	clearSort?: string;
	/** Defaults to `"No results"`. */
	emptyLabel?: string;
	/** Defaults to `"First page"`. */
	first?: string;
	/** Defaults to `"Go to page"`. */
	goToPage?: string;
	/** Defaults to `"Last page"`. */
	last?: string;
	/** Defaults to `"Next page"`. */
	next?: string;
	/** Defaults to `(page, totalPages, totalItems) => \`Page ${page} of ${totalPages} (${totalItems} total)\`` . */
	pageLabel?: (page: number, totalPages: number, totalItems: number) => ReactNode;
	/** Defaults to `"Rows per page"`. */
	pageSize?: string;
	/** Defaults to `"Previous page"`. */
	previous?: string;
	/** Defaults to `"Sort ascending"`. */
	sortAscending?: string;
	/** Defaults to `"Sort descending"`. */
	sortDescending?: string;
};

type Props<TData> = {
	actions?: ReactNode;
	columns: readonly DataTableColumn<TData>[];
	data: readonly TData[];
	getRowId: (row: TData) => string | number;
	getRowClassName?: (row: TData) => string;
	isLoading?: boolean;
	labels?: DataTableCardLabels;
	onRowClick?: (row: TData) => void;
	pagination?: DataTablePaginationState;
	rowHeight?: number;
	skeletonRows?: number;
	sort?: DataTableSortState;
	title: ReactNode;
};

function withLabels(
	pagination: DataTablePaginationState | undefined,
	totalItems: number,
	labels: DataTableCardLabels,
): DataTablePagination | undefined {
	if (!pagination) {
		return undefined;
	}

	return {
		...pagination,
		firstLabel: labels.first ?? 'First page',
		goToPageLabel: labels.goToPage ?? 'Go to page',
		lastLabel: labels.last ?? 'Last page',
		nextLabel: labels.next ?? 'Next page',
		pageLabel: (page, totalPages) =>
			(
				labels.pageLabel ??
				((p: number, tp: number, ti: number) => `Page ${p} of ${tp} (${ti} total)`)
			)(page, totalPages, totalItems),
		pageSizeLabel: labels.pageSize ?? 'Rows per page',
		previousLabel: labels.previous ?? 'Previous page',
	};
}

function withSortLabels(
	sort: DataTableSortState | undefined,
	labels: DataTableCardLabels,
): DataTableSort | undefined {
	if (!sort) {
		return undefined;
	}

	return {
		...sort,
		ascendingLabel: labels.sortAscending ?? 'Sort ascending',
		clearLabel: labels.clearSort ?? 'Clear sort',
		descendingLabel: labels.sortDescending ?? 'Sort descending',
	};
}

export function DataTableCard<TData>({
	actions,
	columns,
	data,
	getRowId,
	getRowClassName,
	isLoading,
	labels = {},
	onRowClick,
	pagination,
	rowHeight,
	skeletonRows,
	sort,
	title,
}: Props<TData>) {
	const [stableTotalItems, setStableTotalItems] = useState(pagination?.totalItems ?? 0);
	if (!isLoading && pagination && pagination.totalItems !== stableTotalItems) {
		setStableTotalItems(pagination.totalItems);
	}
	const totalItems = isLoading ? stableTotalItems : (pagination?.totalItems ?? 0);

	return (
		<Card className='min-h-68 shrink-0'>
			<CardHeader className='border-b'>
				<div className='flex flex-wrap items-center justify-between gap-2'>
					<CardTitle>{title}</CardTitle>
					{actions ? <div className='-my-2.5 flex flex-wrap gap-2'>{actions}</div> : null}
				</div>
			</CardHeader>
			<CardContent>
				<DataTable
					columns={columns}
					data={data}
					emptyLabel={labels.emptyLabel ?? 'No results'}
					getRowClassName={getRowClassName}
					getRowId={getRowId}
					isLoading={isLoading}
					onRowClick={onRowClick}
					pagination={withLabels(pagination, totalItems, labels)}
					rowHeight={rowHeight}
					skeletonRows={skeletonRows}
					sort={withSortLabels(sort, labels)}
				/>
			</CardContent>
		</Card>
	);
}
