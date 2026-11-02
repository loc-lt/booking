import { cn } from 'cn';
import { type CSSProperties, type ReactNode, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Skeleton } from '../ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Icon } from './icon';
import {
	type DataTableColumn,
	type DataTablePagination,
	type DataTableSort,
	SortOrder,
	type SortParam,
} from './types';

const DEFAULT_PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

type Props<TData> = {
	columns: readonly DataTableColumn<TData>[];
	data: readonly TData[];
	emptyLabel: string;
	getRowId: (row: TData) => string | number;
	getRowClassName?: (row: TData) => string;
	getRowStyle?: (row: TData) => CSSProperties;
	isLoading?: boolean;
	onRowClick?: (row: TData) => void;
	pagination?: DataTablePagination;
	/** Actual rendered row height in px — used to keep table height constant across page sizes and result counts. Defaults to 38 (single-line rows, measured — `p-2` cell padding plus `text-sm`'s line height); pass the real value for multi-line cells (e.g. 53 for a two-line name+username cell). */
	rowHeight?: number;
	skeletonRows?: number;
	sort?: DataTableSort;
};

const alignClassNames = {
	center: 'text-center',
	left: 'text-left',
	right: 'text-right',
} as const;

const headerContentClassNames = {
	center: 'justify-center text-center',
	left: 'justify-start text-left',
	right: 'justify-end text-right',
} as const;

function getColumnSort(sorts: SortParam[], sortKey: string) {
	return sorts.find((sort) => sort.sortBy === sortKey);
}

type PageNumberInputProps = {
	ariaLabel: string;
	currentPage: number;
	totalPages: number;
	onPageChange: (page: number) => void;
};

function PageNumberInput({
	ariaLabel,
	currentPage,
	totalPages,
	onPageChange,
}: PageNumberInputProps) {
	// The parent remounts this input (via `key={current_page}`) whenever the page
	// changes elsewhere, so initializing from `currentPage` keeps it in sync.
	const [value, setValue] = useState(String(currentPage));

	const commit = () => {
		const parsed = Number(value);

		if (!Number.isFinite(parsed) || parsed < 1) {
			setValue(String(currentPage));
			return;
		}

		const nextPage = Math.min(Math.max(1, Math.floor(parsed)), totalPages);

		setValue(String(nextPage));

		if (nextPage !== currentPage) {
			onPageChange(nextPage);
		}
	};

	return (
		<Input
			aria-label={ariaLabel}
			// `md:text-xs`, not just `text-xs` — `Input`'s own base classes set
			// `md:text-sm`, and a bare `text-xs` here doesn't conflict with that
			// more-specific variant in tailwind-merge's eyes, so without it this
			// renders at 14px/20px line-height (not 12px/16px) on any desktop-
			// width viewport — taller than the fixed `h-8` box expects, which
			// shifts the digit off-center next to the icon buttons beside it.
			className='h-8 w-12 px-1 text-center text-xs md:text-xs'
			inputMode='numeric'
			onBlur={() => setValue(String(currentPage))}
			onChange={(event) => setValue(event.target.value)}
			onKeyDown={(event) => {
				if (event.key === 'Enter') {
					event.preventDefault();
					commit();
				}
			}}
			value={value}
		/>
	);
}

function getNextSorts(sorts: SortParam[], sortKey: string) {
	const currentSort = getColumnSort(sorts, sortKey);

	if (!currentSort) {
		return [...sorts, { sortBy: sortKey, sortOrder: SortOrder.Asc }];
	}

	if (currentSort.sortOrder === SortOrder.Asc) {
		return sorts.map((sort) =>
			sort.sortBy === sortKey ? { ...sort, sortOrder: SortOrder.Desc } : sort,
		);
	}

	return sorts.filter((sort) => sort.sortBy !== sortKey);
}

type SortableHeaderButtonProps = {
	align: keyof typeof alignClassNames;
	ariaLabel: string;
	children: ReactNode;
	columnSort?: SortParam;
	onClick: () => void;
};

function SortableHeaderButton({
	align,
	ariaLabel,
	children,
	columnSort,
	onClick,
}: SortableHeaderButtonProps) {
	return (
		<Button
			aria-label={ariaLabel}
			className={cn(
				'text-foreground -mx-2 h-auto min-h-7 w-full px-2 py-1 font-semibold',
				headerContentClassNames[align],
			)}
			onClick={onClick}
			size='sm'
			type='button'
			variant='ghost'
		>
			<span>{children}</span>
			<Icon
				className={cn('text-muted-foreground size-3', columnSort && 'text-foreground')}
				name={
					!columnSort
						? 'ArrowUpDown'
						: columnSort.sortOrder === SortOrder.Asc
							? 'ArrowUp'
							: 'ArrowDown'
				}
			/>
		</Button>
	);
}

export function DataTable<TData>({
	columns,
	data,
	emptyLabel,
	getRowId,
	getRowClassName,
	getRowStyle,
	isLoading,
	onRowClick,
	pagination,
	rowHeight = 38,
	skeletonRows,
	sort,
}: Props<TData>) {
	// Preserve last known totalPages so the pagination footer doesn't flicker
	// back to "1" while a new page is loading. Render-time setState is the
	// React-sanctioned pattern for deriving state from props changes.
	const [stableTotalPages, setStableTotalPages] = useState(pagination?.totalPages ?? 1);
	if (!isLoading && pagination && pagination.totalPages !== stableTotalPages) {
		setStableTotalPages(pagination.totalPages);
	}
	const totalPages = isLoading ? stableTotalPages : (pagination?.totalPages ?? 1);
	const pageSizeOptions = pagination?.pageSizeOptions ?? DEFAULT_PAGE_SIZE_OPTIONS;

	const rowCount = skeletonRows ?? pagination?.pageSize ?? 10;

	// Header row (TableHead's h-10) is 40px tall.
	const skeletonHeight = 40 + rowCount * rowHeight;

	return (
		<div className='border-border bg-card max-w-full min-w-0 overflow-x-auto rounded-md border'>
			{isLoading ? (
				<Skeleton className='rounded-none' style={{ height: skeletonHeight }} />
			) : (
				<Table className='min-w-max'>
					<TableHeader className='bg-muted/60'>
						<TableRow>
							{columns.map((column) => {
								const columnSort =
									column.sortKey && sort ? getColumnSort(sort.sorts, column.sortKey) : undefined;

								return (
									<TableHead
										className={cn(alignClassNames[column.align ?? 'left'], column.headerClassName)}
										key={column.id}
									>
										{column.sortKey && sort ? (
											<SortableHeaderButton
												align={column.align ?? 'left'}
												ariaLabel={
													columnSort?.sortOrder === SortOrder.Asc
														? sort.descendingLabel
														: columnSort?.sortOrder === SortOrder.Desc
															? sort.clearLabel
															: sort.ascendingLabel
												}
												columnSort={columnSort}
												onClick={() =>
													sort.onSortChange(getNextSorts(sort.sorts, column.sortKey ?? column.id))
												}
											>
												{column.header}
											</SortableHeaderButton>
										) : (
											column.header
										)}
									</TableHead>
								);
							})}
						</TableRow>
					</TableHeader>
					<TableBody>
						{data.length === 0 ? (
							<TableRow>
								<TableCell
									className='text-muted-foreground text-center'
									colSpan={columns.length}
									style={{ height: rowCount * rowHeight }}
								>
									{emptyLabel}
								</TableCell>
							</TableRow>
						) : null}

						{data.map((row, index) => (
							<TableRow
								// On an exactly-full page there's no filler row height below this
								// one, so its border-b would sit flush against the pagination
								// footer's border-t — two adjacent 1px borders rendering as one
								// slightly-too-thick hairline. Drop it in that case only; on a
								// partial page the filler space still needs the border to mark
								// the end of real content.
								className={cn(
									index === data.length - 1 && data.length >= rowCount && 'border-b-0',
									onRowClick && 'cursor-pointer',
									getRowClassName?.(row),
								)}
								key={getRowId(row)}
								onClick={onRowClick ? () => onRowClick(row) : undefined}
								style={getRowStyle?.(row)}
							>
								{columns.map((column) => (
									<TableCell
										className={cn(alignClassNames[column.align ?? 'left'], column.className)}
										key={column.id}
									>
										<span className='row-cell-content block'>{column.cell?.(row)}</span>
									</TableCell>
								))}
							</TableRow>
						))}

						{data.length > 0 ? (
							// Always rendered (even at 0 height on an exactly-full page) so this
							// row — not the last real one — is the `tbody`'s last child, which is
							// where `TableBody`'s `[&_tr:last-child]:border-0` strips the border.
							// Otherwise the last real row loses its border on a full page but not
							// a partial one, making the table a hair shorter in the former case.
							<TableRow aria-hidden className='hover:bg-transparent'>
								<TableCell
									className='p-0'
									colSpan={columns.length}
									style={{ height: Math.max(0, rowCount - data.length) * rowHeight }}
								/>
							</TableRow>
						) : null}
					</TableBody>
				</Table>
			)}

			{pagination ? (
				<div className='border-border text-muted-foreground flex flex-wrap items-center justify-end gap-2 border-t px-3 py-2 text-xs/relaxed'>
					<div>{pagination.pageLabel(pagination.currentPage, totalPages)}</div>

					<div className='flex items-center gap-1'>
						<Button
							aria-label={pagination.firstLabel}
							disabled={pagination.currentPage <= 1}
							onClick={() => pagination.onPageChange(1)}
							size='icon'
							type='button'
							variant='ghost'
						>
							<Icon name='ChevronsLeft' />
						</Button>
						<Button
							aria-label={pagination.previousLabel}
							disabled={pagination.currentPage <= 1}
							onClick={() => pagination.onPageChange(pagination.currentPage - 1)}
							size='icon'
							type='button'
							variant='ghost'
						>
							<Icon name='ChevronLeft' />
						</Button>
						<PageNumberInput
							ariaLabel={pagination.goToPageLabel}
							currentPage={pagination.currentPage}
							key={pagination.currentPage}
							onPageChange={pagination.onPageChange}
							totalPages={totalPages}
						/>
						<span className='shrink-0'>/ {totalPages}</span>
						<Button
							aria-label={pagination.nextLabel}
							disabled={pagination.currentPage >= totalPages}
							onClick={() => pagination.onPageChange(pagination.currentPage + 1)}
							size='icon'
							type='button'
							variant='ghost'
						>
							<Icon name='ChevronRight' />
						</Button>
						<Button
							aria-label={pagination.lastLabel}
							disabled={pagination.currentPage >= totalPages}
							onClick={() => pagination.onPageChange(totalPages)}
							size='icon'
							type='button'
							variant='ghost'
						>
							<Icon name='ChevronsRight' />
						</Button>
						<Select
							onValueChange={(v) => pagination.onPageSizeChange(Number(v))}
							value={String(pagination.pageSize)}
						>
							<SelectTrigger
								aria-label={pagination.pageSizeLabel}
								className='h-8 w-auto gap-1 text-xs'
							>
								<SelectValue />
							</SelectTrigger>
							<SelectContent side='top'>
								{pageSizeOptions.map((size) => (
									<SelectItem className='text-xs' key={size} value={String(size)}>
										{size}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
				</div>
			) : null}
		</div>
	);
}
