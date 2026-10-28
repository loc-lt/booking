import {
	ApiError,
	type ResourceType,
	useListResources,
	useListResourceTypes,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { FieldValueView } from '@booking-core/custom-fields';
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
	Skeleton,
} from '@booking-core/ui';
import { useEffect, useState } from 'react';

const ALL_TYPES = 'all';

export function SearchPage() {
	const [resourceTypeId, setResourceTypeId] = useState(ALL_TYPES);
	const resourceTypesQuery = useListResourceTypes();
	const resourcesQuery = useListResources({
		resourceTypeId: resourceTypeId === ALL_TYPES ? undefined : resourceTypeId,
	});

	useEffect(() => {
		if (resourcesQuery.data) {
			trackEvent('booking_search_submitted', {
				resourceTypeId: resourceTypeId === ALL_TYPES ? undefined : resourceTypeId,
				resultsCount: resourcesQuery.data.data.length,
			});
		}
	}, [resourcesQuery.data, resourceTypeId]);

	const resourceTypesById = new Map<string, ResourceType>(
		(resourceTypesQuery.data?.data ?? []).map((type) => [type.id, type]),
	);
	const typeSelectItems = [
		{ value: ALL_TYPES, label: 'All resource types' },
		...(resourceTypesQuery.data?.data ?? []).map((type) => ({ value: type.id, label: type.label })),
	];

	return (
		<div className='mx-auto flex max-w-2xl flex-col gap-4 p-6'>
			<h1 className='text-xl font-semibold'>Search resources</h1>

			<Select
				items={typeSelectItems}
				value={resourceTypeId}
				onValueChange={(value) => setResourceTypeId(value ?? ALL_TYPES)}
			>
				<SelectTrigger className='w-56'>
					<SelectValue />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={ALL_TYPES}>All resource types</SelectItem>
					{resourceTypesQuery.data?.data.map((type) => (
						<SelectItem key={type.id} value={type.id}>
							{type.label}
						</SelectItem>
					))}
				</SelectContent>
			</Select>

			{resourcesQuery.isPending && (
				<div className='flex flex-col gap-2'>
					<Skeleton className='h-16 w-full' />
					<Skeleton className='h-16 w-full' />
				</div>
			)}

			{resourcesQuery.error && (
				<p className='text-destructive text-sm'>
					Couldn't load resources (
					{resourcesQuery.error instanceof ApiError ? resourcesQuery.error.code : 'UNKNOWN_ERROR'}
					).
				</p>
			)}

			{resourcesQuery.data && resourcesQuery.data.data.length === 0 && (
				<p className='text-muted-foreground text-sm'>No resources match.</p>
			)}

			{resourcesQuery.data?.data.map((resource) => {
				const resourceType = resourceTypesById.get(resource.resourceTypeId);
				return (
					<Card key={resource.id}>
						<CardHeader>
							<CardTitle>{resource.label}</CardTitle>
						</CardHeader>
						<CardContent className='flex flex-col gap-1'>
							{resourceType?.fields.map((field) => (
								<FieldValueView
									key={field.key}
									field={field}
									value={resource.customFieldValues[field.key]}
								/>
							))}
						</CardContent>
					</Card>
				);
			})}
		</div>
	);
}
