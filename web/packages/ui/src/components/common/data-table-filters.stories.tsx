import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { DataTableFilters } from './data-table-filters';
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
	title: 'common/DataTableFilters',
	component: DataTableFilters<Filters>,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		applyLabel: 'Apply',
		clearLabel: 'Clear',
		fields: FIELDS,
		resetLabel: 'Reset',
		submitLabel: 'Search',
		// Overridden by `DataTableFiltersDemo`'s own state below — required
		// here only so every story satisfies the component's required props.
		onValueChange: () => {},
		values: {},
	},
} satisfies Meta<typeof DataTableFilters<Filters>>;

export default meta;
type Story = StoryObj<typeof meta>;

function DataTableFiltersDemo(args: Story['args']) {
	const [values, setValues] = useState<Filters>({});

	return (
		<DataTableFilters
			{...args}
			applyLabel={args?.applyLabel ?? 'Apply'}
			clearLabel={args?.clearLabel ?? 'Clear'}
			fields={args?.fields ?? FIELDS}
			resetLabel={args?.resetLabel ?? 'Reset'}
			submitLabel={args?.submitLabel ?? 'Search'}
			values={values}
			onValueChange={(name, value) => setValues((current) => ({ ...current, [name]: value }))}
			onReset={() => setValues({})}
			onSubmit={() => {}}
		/>
	);
}

export const Default: Story = {
	render: (args) => <DataTableFiltersDemo {...args} />,
};
