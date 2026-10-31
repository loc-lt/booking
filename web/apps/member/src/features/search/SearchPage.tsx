import {
	ApiError,
	type ResourceType,
	useListResources,
	useListResourceTypes,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { FieldValueView, isBookingScoped, isResourceScoped } from '@booking-core/custom-fields';
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
	ClearableSelect,
	Skeleton,
} from '@booking-core/ui';
import { useEffect, useState } from 'react';
import { ResourceAvailability } from './ResourceAvailability';

export function SearchPage() {
	const [resourceTypeId, setResourceTypeId] = useState('');
	const resourceTypesQuery = useListResourceTypes();
	const resourcesQuery = useListResources({
		resourceTypeId: resourceTypeId === '' ? undefined : resourceTypeId,
	});
	// Unfiltered, to resolve `reference` fields' values regardless of the selected type.
	const allResourcesQuery = useListResources();
	const referenceOptions: Record<string, { value: string; label: string }[]> = {};
	for (const resource of allResourcesQuery.data?.data ?? []) {
		const existing = referenceOptions[resource.resourceTypeId] ?? [];
		existing.push({ value: resource.id, label: resource.label });
		referenceOptions[resource.resourceTypeId] = existing;
	}

	useEffect(() => {
		if (resourcesQuery.data) {
			trackEvent('booking_search_submitted', {
				resourceTypeId: resourceTypeId === '' ? undefined : resourceTypeId,
				resultsCount: resourcesQuery.data.data.length,
			});
		}
	}, [resourcesQuery.data, resourceTypeId]);

	const resourceTypesById = new Map<string, ResourceType>(
		(resourceTypesQuery.data?.data ?? []).map((type) => [type.id, type]),
	);
	const resourceTypeOptions = (resourceTypesQuery.data?.data ?? []).map((type) => ({
		label: type.label,
		value: type.id,
	}));

	return (
		<div className='mx-auto flex max-w-2xl flex-col gap-4 p-6'>
			<h1 className='text-xl font-semibold'>Search resources</h1>

			<ClearableSelect
				className='w-56'
				clearLabel='Clear'
				emptyLabel='All resource types'
				onValueChange={setResourceTypeId}
				options={resourceTypeOptions}
				value={resourceTypeId}
			/>

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
						<CardContent className='flex flex-col gap-3'>
							{resourceType?.fields.filter(isResourceScoped).map((field) => (
								<FieldValueView
									key={field.key}
									field={field}
									value={resource.customFieldValues[field.key]}
									referenceOptions={referenceOptions}
								/>
							))}
							<ResourceAvailability
								resourceId={resource.id}
								resourceTypeId={resource.resourceTypeId}
								fields={resourceType?.fields.filter(isBookingScoped) ?? []}
							/>
						</CardContent>
					</Card>
				);
			})}
		</div>
	);
}
