import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { Button } from '../ui/button';
import { DataTableCard } from './data-table-card';
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
	title: 'common/DataTableCard',
	component: DataTableCard<Row>,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		title: 'Bookings',
		columns: COLUMNS,
		data: ROWS,
		getRowId: (row: Row) => row.id,
	},
} satisfies Meta<typeof DataTableCard<Row>>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Loading: Story = {
	args: { isLoading: true },
};

export const WithActions: Story = {
	args: {
		actions: (
			<Button size='sm' variant='outline'>
				Refresh
			</Button>
		),
	},
};

function WithPaginationAndSortDemo(args: Story['args']) {
	const [page, setPage] = useState(1);
	const [pageSize, setPageSize] = useState(10);
	const [sorts, setSorts] = useState<SortParam[]>([
		{ sortBy: 'resource', sortOrder: SortOrder.Asc },
	]);

	return (
		<DataTableCard
			{...args}
			title={args?.title ?? 'Bookings'}
			columns={args?.columns ?? COLUMNS}
			data={args?.data ?? ROWS}
			getRowId={args?.getRowId ?? ((row: Row) => row.id)}
			pagination={{
				currentPage: page,
				pageSize,
				totalItems: ROWS.length,
				totalPages: 1,
				onPageChange: setPage,
				onPageSizeChange: setPageSize,
			}}
			sort={{ onSortChange: setSorts, sorts }}
		/>
	);
}

export const WithPaginationAndSort: Story = {
	render: (args) => <WithPaginationAndSortDemo {...args} />,
};
