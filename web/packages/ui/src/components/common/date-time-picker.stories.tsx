import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { DateTimePicker } from './date-time-picker';

const meta = {
	title: 'common/DateTimePicker',
	component: DateTimePicker,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
	args: {
		clearLabel: 'Clear',
		placeholder: 'Pick a date and time',
		submitLabel: 'Apply',
		// Overridden by `DateTimePickerDemo`'s own state below — required here
		// only so every story satisfies the component's required props.
		onValueChange: () => {},
		value: '',
	},
} satisfies Meta<typeof DateTimePicker>;

export default meta;
type Story = StoryObj<typeof meta>;

function DateTimePickerDemo(args: Story['args']) {
	const [value, setValue] = useState(args?.value ?? '');
	return (
		<DateTimePicker
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
	render: (args) => <DateTimePickerDemo {...args} />,
};

export const WithValue: Story = {
	args: { value: '2026-12-15 14:30:00' },
	render: (args) => <DateTimePickerDemo {...args} />,
};
