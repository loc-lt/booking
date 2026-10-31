import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { DataTable } from './data-table';
import { type DataTableColumn, SortOrder, type SortParam } from './types';

type Row = { id: string; resource: string; member: string; time: string };

const ROWS: Row[] = [
	{ id: '1', resource: 'Hot desk 3', member: 'Alex Chen', time: '9:00 AM – 5:00 PM' },
	{ id: '2', resource: 'Meeting Room A', member: 'Priya Patel', time: '2:00 PM – 2:30 PM' },
	{ id: '3', resource: 'Phone Booth 1', member: 'Jordan Lee', time: '11:00 AM – 11:15 AM' },
];

const COLUMNS: DataTableColumn<Row>[] = [
	{ id: 'resource', header: 'Resource', cell: (row) => row.resource, sortKey: 'resource' },
	{ id: 'member', header: 'Member', cell: (row) => row.member, sortKey: 'member' },
	{ id: 'time', header: 'Time', cell: (row) => row.time },
];

const meta = {
	title: 'common/DataTable',
	component: DataTable<Row>,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		columns: COLUMNS,
		data: ROWS,
		emptyLabel: 'No results',
		getRowId: (row: Row) => row.id,
	},
} satisfies Meta<typeof DataTable<Row>>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Loading: Story = {
	args: { isLoading: true },
};

export const EmptyState: Story = {
	args: { data: [] },
};

function WithPaginationAndSortDemo(args: Story['args']) {
	const [page, setPage] = useState(1);
	const [pageSize, setPageSize] = useState(10);
	const [sorts, setSorts] = useState<SortParam[]>([
		{ sortBy: 'resource', sortOrder: SortOrder.Asc },
	]);

	return (
		<DataTable
			{...args}
			columns={args?.columns ?? COLUMNS}
			data={args?.data ?? ROWS}
			emptyLabel={args?.emptyLabel ?? 'No results'}
			getRowId={args?.getRowId ?? ((row: Row) => row.id)}
			pagination={{
				currentPage: page,
				pageSize,
				totalItems: ROWS.length,
				totalPages: 1,
				firstLabel: 'First page',
				goToPageLabel: 'Go to page',
				lastLabel: 'Last page',
				nextLabel: 'Next page',
				onPageChange: setPage,
				onPageSizeChange: setPageSize,
				pageLabel: (p, total) => `Page ${p} of ${total}`,
				pageSizeLabel: 'Rows per page',
				previousLabel: 'Previous page',
			}}
			sort={{
				ascendingLabel: 'Sort ascending',
				clearLabel: 'Clear sort',
				descendingLabel: 'Sort descending',
				onSortChange: setSorts,
				sorts,
			}}
		/>
	);
}

export const WithPaginationAndSort: Story = {
	render: (args) => <WithPaginationAndSortDemo {...args} />,
};
