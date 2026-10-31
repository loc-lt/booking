import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './button';
import { Tooltip, TooltipContent, TooltipTrigger } from './tooltip';

const meta = {
	title: 'ui/Tooltip',
	component: Tooltip,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
} satisfies Meta<typeof Tooltip>;

export default meta;
type Story = StoryObj<typeof meta>;

// The decorator in .storybook/preview.tsx already wraps every story in a
// `TooltipProvider`, matching how `CoreAppProvider` wraps each real app.
export const Default: Story = {
	render: () => (
		<Tooltip>
			<TooltipTrigger render={<Button variant='outline'>Hover me</Button>} />
			<TooltipContent>Refresh the list</TooltipContent>
		</Tooltip>
	),
};
