import type { Meta, StoryObj } from '@storybook/react-vite';
import { type ComponentProps, useState } from 'react';
import { ClearableSelect } from './clearable-select';

const RESOURCE_TYPES = [
	{ value: 'hot-desk', label: 'Hot desk' },
	{ value: 'meeting-room', label: 'Meeting room' },
	{ value: 'phone-booth', label: 'Phone booth' },
];

const meta = {
	title: 'common/ClearableSelect',
	component: ClearableSelect,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		className: 'w-56',
		clearLabel: 'Clear',
		emptyLabel: 'All resource types',
		options: RESOURCE_TYPES,
		// Overridden by `ClearableSelectDemo`'s own state below — required here
		// only so every story satisfies the component's required props.
		onValueChange: () => {},
		value: '',
	},
} satisfies Meta<typeof ClearableSelect>;

export default meta;
type Story = StoryObj<typeof meta>;

function ClearableSelectDemo(props: ComponentProps<typeof ClearableSelect>) {
	const [value, setValue] = useState(props.value);
	return <ClearableSelect {...props} onValueChange={setValue} value={value} />;
}

export const Empty: Story = {
	args: { value: '' },
	render: (args) => <ClearableSelectDemo {...args} />,
};

export const WithValue: Story = {
	args: { value: 'meeting-room' },
	render: (args) => <ClearableSelectDemo {...args} />,
};
