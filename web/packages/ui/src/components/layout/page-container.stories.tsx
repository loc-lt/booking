import type { Meta, StoryObj } from '@storybook/react-vite';
import { PageContainer } from './page-container';

const meta = {
	title: 'layout/PageContainer',
	component: PageContainer,
	tags: ['autodocs'],
	parameters: { layout: 'fullscreen' },
	args: {
		children: (
			<div className='text-muted-foreground rounded-md border border-dashed p-6 text-sm'>
				Page content goes here.
			</div>
		),
	},
} satisfies Meta<typeof PageContainer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
