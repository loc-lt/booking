import type { Meta, StoryObj } from '@storybook/react-vite';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './table';

const ROWS = [
	{ id: '1', resource: 'Hot desk 3', member: 'Alex Chen', time: '9:00 AM – 5:00 PM' },
	{ id: '2', resource: 'Meeting Room A', member: 'Priya Patel', time: '2:00 PM – 2:30 PM' },
	{ id: '3', resource: 'Phone Booth 1', member: 'Jordan Lee', time: '11:00 AM – 11:15 AM' },
];

const meta = {
	title: 'ui/Table',
	component: Table,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
} satisfies Meta<typeof Table>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
	render: () => (
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead>Resource</TableHead>
					<TableHead>Member</TableHead>
					<TableHead>Time</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{ROWS.map((row) => (
					<TableRow key={row.id}>
						<TableCell>{row.resource}</TableCell>
						<TableCell>{row.member}</TableCell>
						<TableCell>{row.time}</TableCell>
					</TableRow>
				))}
			</TableBody>
		</Table>
	),
};
