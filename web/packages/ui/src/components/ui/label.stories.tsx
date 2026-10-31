import type { Meta, StoryObj } from '@storybook/react-vite';
import { Input } from './input';
import { Label } from './label';

const meta = {
	title: 'ui/Label',
	component: Label,
	tags: ['autodocs'],
	args: {
		children: 'Resource label',
	},
} satisfies Meta<typeof Label>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithInput: Story = {
	render: () => (
		<div className='flex flex-col gap-1.5'>
			<Label htmlFor='resource-label-story'>Resource label</Label>
			<Input id='resource-label-story' placeholder='Hot desk 3' />
		</div>
	),
};
