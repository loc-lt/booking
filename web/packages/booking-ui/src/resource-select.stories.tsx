import type { Resource } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { ResourceSelect } from './resource-select';

const RESOURCE_TYPE_ID = '0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c';
const SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';

function makeResource(id: string, label: string): Resource {
	return {
		id,
		resourceTypeId: RESOURCE_TYPE_ID,
		siteId: SITE_ID,
		label,
		customFieldValues: {},
		createdAt: '2026-12-01T00:00:00+07:00',
		updatedAt: '2026-12-01T00:00:00+07:00',
	};
}

const RESOURCES: Resource[] = [
	makeResource('0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d', 'Meeting Room A'),
	makeResource('0193f4c4-4f90-7b8d-bc7f-6e4a1b0c9d8e', 'Meeting Room B'),
	makeResource('0193f4c4-5a01-7c9e-cd80-7f5b2c1d0e9f', 'Phone Booth 1'),
];

const meta = {
	title: 'booking-ui/ResourceSelect',
	component: ResourceSelect,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		resources: RESOURCES,
		onValueChange: () => {},
	},
} satisfies Meta<typeof ResourceSelect>;

export default meta;
type Story = StoryObj<typeof meta>;

function ResourceSelectDemo(args: Story['args']) {
	const [value, setValue] = useState(args?.value);
	return (
		<ResourceSelect
			{...args}
			onValueChange={setValue}
			resources={args?.resources ?? RESOURCES}
			value={value}
		/>
	);
}

export const Default: Story = {
	render: (args) => <ResourceSelectDemo {...args} />,
};

export const Selected: Story = {
	args: { value: RESOURCES[0]?.id },
	render: (args) => <ResourceSelectDemo {...args} />,
};

export const Empty: Story = {
	args: { resources: [] },
	render: (args) => <ResourceSelectDemo {...args} />,
};

export const Disabled: Story = {
	args: { value: RESOURCES[0]?.id, disabled: true },
	render: (args) => <ResourceSelectDemo {...args} />,
};

export const CustomLabel: Story = {
	args: { renderLabel: (resource) => `📍 ${resource.label}` },
	render: (args) => <ResourceSelectDemo {...args} />,
};
