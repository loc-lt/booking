import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { DatePicker } from './date-picker';

const meta = {
	title: 'common/DatePicker',
	component: DatePicker,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
	args: {
		clearLabel: 'Clear',
		placeholder: 'Pick a date',
		submitLabel: 'Apply',
		// Overridden by `DatePickerDemo`'s own state below — required here only
		// so every story satisfies the component's required props.
		onValueChange: () => {},
		value: '',
	},
} satisfies Meta<typeof DatePicker>;

export default meta;
type Story = StoryObj<typeof meta>;

function DatePickerDemo(args: Story['args']) {
	const [value, setValue] = useState(args?.value ?? '');
	return (
		<DatePicker
			{...args}
			clearLabel={args?.clearLabel ?? 'Clear'}
			submitLabel={args?.submitLabel ?? 'Apply'}
			value={value}
			onValueChange={setValue}
		/>
	);
}

export const Empty: Story = {
	args: { value: '' },
	render: (args) => <DatePickerDemo {...args} />,
};

export const WithValue: Story = {
	args: { value: '2026-12-15' },
	render: (args) => <DatePickerDemo {...args} />,
};
