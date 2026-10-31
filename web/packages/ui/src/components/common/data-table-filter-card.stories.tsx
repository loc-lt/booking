import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { DataTableFilterCard } from './data-table-filter-card';
import type { DataTableFilterField, FilterValues } from './types';

type Filters = FilterValues & { search?: string; resourceTypeId?: string };

const FIELDS: DataTableFilterField<Filters>[] = [
	{ name: 'search', label: 'Search', type: 'text', placeholder: 'Search bookings…' },
	{
		name: 'resourceTypeId',
		label: 'Resource type',
		type: 'select',
		emptyLabel: 'All resource types',
		options: [
			{ value: 'hot-desk', label: 'Hot desk' },
			{ value: 'meeting-room', label: 'Meeting room' },
		],
	},
];

const meta = {
	title: 'common/DataTableFilterCard',
	component: DataTableFilterCard<Filters>,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		title: 'Filters',
		fields: FIELDS,
		// Overridden by `DataTableFilterCardDemo`'s own state below — required
		// here only so every story satisfies the component's required props.
		onReset: () => {},
		onSubmit: () => {},
		onValueChange: () => {},
		values: {},
	},
} satisfies Meta<typeof DataTableFilterCard<Filters>>;

export default meta;
type Story = StoryObj<typeof meta>;

function DataTableFilterCardDemo(args: Story['args']) {
	const [values, setValues] = useState<Filters>({});

	return (
		<DataTableFilterCard
			{...args}
			fields={args?.fields ?? FIELDS}
			title={args?.title ?? 'Filters'}
			values={values}
			onValueChange={(name, value) => setValues((current) => ({ ...current, [name]: value }))}
			onReset={() => setValues({})}
			onSubmit={() => {}}
		/>
	);
}

export const Default: Story = {
	render: (args) => <DataTableFilterCardDemo {...args} />,
};
