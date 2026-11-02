import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './button';
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from './dropdown-menu';

const meta = {
	title: 'ui/DropdownMenu',
	component: DropdownMenu,
	tags: ['autodocs'],
} satisfies Meta<typeof DropdownMenu>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
	render: () => (
		<DropdownMenu>
			<DropdownMenuTrigger render={<Button variant='outline'>Open menu</Button>} />
			<DropdownMenuContent align='start'>
				<DropdownMenuGroup>
					<DropdownMenuLabel>Resource types</DropdownMenuLabel>
				</DropdownMenuGroup>
				<DropdownMenuSeparator />
				<DropdownMenuItem onClick={() => {}}>Edit</DropdownMenuItem>
				<DropdownMenuItem onClick={() => {}}>Duplicate</DropdownMenuItem>
				<DropdownMenuSeparator />
				<DropdownMenuItem onClick={() => {}} variant='destructive'>
					Delete
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	),
};
