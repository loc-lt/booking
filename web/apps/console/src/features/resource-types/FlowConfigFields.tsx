import type { FlowConfig } from '@booking-core/api-client';
import {
	Checkbox,
	Input,
	Label,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@booking-core/ui';

export const DEFAULT_FLOW_CONFIG: FlowConfig = {
	confirmation: 'instant',
	checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
	cancellation: { allowedUntilMinutesBefore: 60 },
};

const CONFIRMATION_ITEMS = [
	{ value: 'instant', label: 'Instant' },
	{ value: 'approval', label: 'Needs approval' },
];

export function FlowConfigFields({
	value,
	onChange,
	idPrefix,
}: {
	value: FlowConfig;
	onChange: (next: FlowConfig) => void;
	idPrefix: string;
}) {
	return (
		<div className='flex flex-col gap-4'>
			<div className='space-y-1'>
				<Label htmlFor={`${idPrefix}-confirmation`}>Confirmation</Label>
				<Select
					items={CONFIRMATION_ITEMS}
					value={value.confirmation}
					onValueChange={(next) =>
						onChange({ ...value, confirmation: (next ?? 'instant') as FlowConfig['confirmation'] })
					}
				>
					<SelectTrigger id={`${idPrefix}-confirmation`} className='w-48'>
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{CONFIRMATION_ITEMS.map((item) => (
							<SelectItem key={item.value} value={item.value}>
								{item.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
			</div>

			<div className='flex flex-col gap-2'>
				<div className='flex items-center gap-2'>
					<Checkbox
						id={`${idPrefix}-check-in-required`}
						checked={value.checkIn.required}
						onCheckedChange={(checked) =>
							onChange({ ...value, checkIn: { ...value.checkIn, required: Boolean(checked) } })
						}
					/>
					<Label htmlFor={`${idPrefix}-check-in-required`}>Check-in required</Label>
				</div>
				<div className='flex gap-4'>
					<div className='flex-1 space-y-1'>
						<Label htmlFor={`${idPrefix}-opens-minutes-before`}>Opens (minutes before start)</Label>
						<Input
							id={`${idPrefix}-opens-minutes-before`}
							type='number'
							min={0}
							value={value.checkIn.opensMinutesBefore}
							onChange={(e) =>
								onChange({
									...value,
									checkIn: { ...value.checkIn, opensMinutesBefore: Number(e.target.value) },
								})
							}
						/>
					</div>
					<div className='flex-1 space-y-1'>
						<Label htmlFor={`${idPrefix}-no-show-after`}>No-show after (minutes)</Label>
						<Input
							id={`${idPrefix}-no-show-after`}
							type='number'
							min={0}
							value={value.checkIn.noShowAfterMinutes}
							onChange={(e) =>
								onChange({
									...value,
									checkIn: { ...value.checkIn, noShowAfterMinutes: Number(e.target.value) },
								})
							}
						/>
					</div>
				</div>
			</div>

			<div className='space-y-1'>
				<Label htmlFor={`${idPrefix}-cancellation`}>
					Cancellation allowed until (minutes before start)
				</Label>
				<Input
					id={`${idPrefix}-cancellation`}
					type='number'
					min={0}
					className='w-48'
					value={value.cancellation.allowedUntilMinutesBefore}
					onChange={(e) =>
						onChange({
							...value,
							cancellation: { allowedUntilMinutesBefore: Number(e.target.value) },
						})
					}
				/>
			</div>
		</div>
	);
}
