import type { ReactNode } from 'react';

export const SortOrder = {
	Asc: 'asc',
	Desc: 'desc',
} as const;
export type SortOrder = (typeof SortOrder)[keyof typeof SortOrder];

export type SortParam = {
	sortBy: string;
	sortOrder: SortOrder;
};

/** Page-count fields a consumer's paginated API response is expected to carry. */
export type Pagination = {
	currentPage: number;
	pageSize: number;
	totalItems: number;
	totalPages: number;
};

export type FilterValues = Record<string, string | undefined>;

export type FilterOption<TValue extends string = string> = {
	label: ReactNode;
	value: TValue;
};

type BaseFilterField<TFilters extends FilterValues, TName extends keyof TFilters & string> = {
	className?: string;
	disabled?: boolean;
	label: ReactNode;
	name: TName;
	placeholder?: string;
};

type TextDataTableFilterField<
	TFilters extends FilterValues,
	TName extends keyof TFilters & string,
> = BaseFilterField<TFilters, TName> & {
	type: 'text';
};

type DateDataTableFilterField<
	TFilters extends FilterValues,
	TName extends keyof TFilters & string,
> = BaseFilterField<TFilters, TName> & {
	type: 'date';
};

type DateTimeDataTableFilterField<
	TFilters extends FilterValues,
	TName extends keyof TFilters & string,
> = BaseFilterField<TFilters, TName> & {
	defaultTime?: string;
	type: 'datetime';
};

type SelectDataTableFilterField<
	TFilters extends FilterValues,
	TName extends keyof TFilters & string,
> = BaseFilterField<TFilters, TName> & {
	emptyLabel?: ReactNode;
	options: readonly FilterOption<Extract<TFilters[TName], string>>[];
	type: 'select';
};

export type DataTableFilterField<
	TFilters extends FilterValues,
	TName extends keyof TFilters & string = keyof TFilters & string,
> =
	| TextDataTableFilterField<TFilters, TName>
	| DateDataTableFilterField<TFilters, TName>
	| DateTimeDataTableFilterField<TFilters, TName>
	| SelectDataTableFilterField<TFilters, TName>;

export type DataTableColumn<TData> = {
	align?: 'left' | 'center' | 'right';
	cell?: (row: TData) => ReactNode;
	className?: string;
	header: ReactNode;
	headerClassName?: string;
	id: string;
	sortKey?: string;
};

export type DataTablePagination = Pagination & {
	firstLabel: string;
	goToPageLabel: string;
	lastLabel: string;
	nextLabel: string;
	onPageChange: (page: number) => void;
	onPageSizeChange: (pageSize: number) => void;
	pageLabel: (page: number, totalPages: number) => ReactNode;
	/** Defaults to `[10, 20, 50, 100]`. */
	pageSizeOptions?: readonly number[];
	pageSizeLabel: string;
	previousLabel: string;
};

export type DataTablePaginationState = Pagination &
	Pick<DataTablePagination, 'onPageChange' | 'onPageSizeChange' | 'pageSizeOptions'>;

export type DataTableSort = {
	ascendingLabel: string;
	clearLabel: string;
	descendingLabel: string;
	onSortChange: (sorts: SortParam[]) => void;
	sorts: SortParam[];
};

export type DataTableSortState = Pick<DataTableSort, 'onSortChange' | 'sorts'>;
