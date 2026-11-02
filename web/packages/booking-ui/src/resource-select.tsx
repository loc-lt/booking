import type { Resource } from '@booking-core/api-client';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@booking-core/ui';

export interface ResourceSelectProps {
	resources: Resource[];
	value?: string;
	onValueChange: (resourceId: string) => void;
	placeholder?: string;
	disabled?: boolean;
	className?: string;
	/** Defaults to a resource's own `label`. */
	renderLabel?: (resource: Resource) => string;
}

export function ResourceSelect({
	resources,
	value,
	onValueChange,
	placeholder = 'Select a resource',
	disabled,
	className,
	renderLabel = (resource) => resource.label,
}: ResourceSelectProps) {
	return (
		<Select
			disabled={disabled ?? resources.length === 0}
			items={resources.map((resource) => ({ value: resource.id, label: renderLabel(resource) }))}
			onValueChange={(next) => next !== null && onValueChange(next)}
			value={value ?? ''}
		>
			<SelectTrigger aria-label={placeholder} className={className}>
				<SelectValue placeholder={placeholder} />
			</SelectTrigger>
			<SelectContent>
				{resources.map((resource) => (
					<SelectItem key={resource.id} value={resource.id}>
						{renderLabel(resource)}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}
