import type { FieldDefinition } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { FieldValueView } from './FieldValueView';

const meta = {
	title: 'custom-fields/FieldValueView',
	component: FieldValueView,
	tags: ['autodocs'],
} satisfies Meta<typeof FieldValueView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Text: Story = {
	args: {
		field: { key: 'floor', label: 'Floor', type: 'text' },
		value: '3rd floor',
	},
};

export const BooleanField: Story = {
	args: {
		field: { key: 'hasProjector', label: 'Has projector', type: 'boolean' },
		value: true,
	},
};

export const Select: Story = {
	args: {
		field: {
			key: 'equipment',
			label: 'Equipment',
			type: 'select',
			options: [{ value: 'whiteboard', label: 'Whiteboard' }],
		} satisfies FieldDefinition,
		value: 'whiteboard',
	},
};

export const Reference: Story = {
	args: {
		field: {
			key: 'building',
			label: 'Building',
			type: 'reference',
			validation: { targetResourceTypeId: 'building-type' },
		},
		value: 'north',
		referenceOptions: {
			'building-type': [{ value: 'north', label: 'North building' }],
		},
	},
};

export const Empty: Story = {
	args: {
		field: { key: 'floor', label: 'Floor', type: 'text' },
		value: undefined,
	},
};
