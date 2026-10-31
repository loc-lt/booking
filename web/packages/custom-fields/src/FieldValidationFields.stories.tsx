import type { FieldValidation } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { FieldValidationFields } from './FieldValidationFields';

const meta = {
	title: 'custom-fields/FieldValidationFields',
	component: FieldValidationFields,
	tags: ['autodocs'],
	args: {
		idPrefix: 'field-validation-story',
		// `type` is overridden by every story below; `value`/`onChange` are
		// overridden by `FieldValidationFieldsDemo`'s own state — all required
		// here only so every story satisfies the component's required props.
		type: 'text',
		value: undefined,
		onChange: () => {},
	},
} satisfies Meta<typeof FieldValidationFields>;

export default meta;
type Story = StoryObj<typeof meta>;

function FieldValidationFieldsDemo(args: Story['args']) {
	const [value, setValue] = useState<FieldValidation | undefined>(args?.value);
	return (
		<FieldValidationFields
			{...args}
			idPrefix={args?.idPrefix ?? 'field-validation-story'}
			type={args?.type ?? 'text'}
			value={value}
			onChange={setValue}
		/>
	);
}

export const Text: Story = {
	args: { type: 'text' },
	render: (args) => <FieldValidationFieldsDemo {...args} />,
};

export const Numeric: Story = {
	args: { type: 'integer' },
	render: (args) => <FieldValidationFieldsDemo {...args} />,
};

export const ArrayField: Story = {
	args: { type: 'multi_select' },
	render: (args) => <FieldValidationFieldsDemo {...args} />,
};

export const NoValidation: Story = {
	args: { type: 'boolean' },
	render: (args) => <FieldValidationFieldsDemo {...args} />,
};
