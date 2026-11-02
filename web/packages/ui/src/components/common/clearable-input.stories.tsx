import type { Meta, StoryObj } from '@storybook/react-vite';
import { type ComponentProps, useState } from 'react';
import { ClearableInput } from './clearable-input';

const meta = {
	title: 'common/ClearableInput',
	component: ClearableInput,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		className: 'w-56',
		clearLabel: 'Clear',
		placeholder: 'Phone booth',
		// Overridden by `ClearableInputDemo`'s own state below — required here
		// only so every story satisfies the component's required props.
		onChange: () => {},
		onClear: () => {},
		value: '',
	},
} satisfies Meta<typeof ClearableInput>;

export default meta;
type Story = StoryObj<typeof meta>;

function ClearableInputDemo(props: ComponentProps<typeof ClearableInput>) {
	const [value, setValue] = useState(props.value);
	return (
		<ClearableInput
			{...props}
			onChange={(event) => setValue(event.target.value)}
			onClear={() => setValue('')}
			value={value}
		/>
	);
}

export const Empty: Story = {
	args: { value: '' },
	render: (args) => <ClearableInputDemo {...args} />,
};

export const WithValue: Story = {
	args: { value: 'Phone booth 3' },
	render: (args) => <ClearableInputDemo {...args} />,
};

export const Disabled: Story = {
	args: { disabled: true, value: 'Phone booth 3' },
	render: (args) => <ClearableInputDemo {...args} />,
};
