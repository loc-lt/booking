import {
	ApiError,
	getListResourcesQueryKey,
	type ResourceType,
	useCreateResource,
	useListResources,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { CustomFieldValuesEditor } from '@booking-core/custom-fields';
import {
	Badge,
	Button,
	Card,
	CardContent,
	CardHeader,
	CardTitle,
	Input,
	Label,
	Skeleton,
} from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

// Sites aren't built yet, so new resources land at this fixed demo site.
const DEMO_SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';

export function ResourceTypeCard({ resourceType }: { resourceType: ResourceType }) {
	const queryClient = useQueryClient();
	const [adding, setAdding] = useState(false);
	const [label, setLabel] = useState('');
	const [values, setValues] = useState<Record<string, unknown>>({});
	const createResource = useCreateResource();
	const resourcesQuery = useListResources({ resourceTypeId: resourceType.id });

	function resetForm() {
		setLabel('');
		setValues({});
	}

	function handleCreate() {
		createResource.mutate(
			{
				data: {
					resourceTypeId: resourceType.id,
					siteId: DEMO_SITE_ID,
					label,
					customFieldValues: values,
				},
			},
			{
				onSuccess: () => {
					trackEvent('resource_created', { resourceTypeId: resourceType.id });
					resetForm();
					queryClient.invalidateQueries({
						queryKey: getListResourcesQueryKey({ resourceTypeId: resourceType.id }),
					});
				},
			},
		);
	}

	return (
		<Card>
			<CardHeader>
				<CardTitle className='flex items-center gap-2'>
					{resourceType.label}
					<Badge variant='secondary'>{resourceType.key}</Badge>
				</CardTitle>
			</CardHeader>
			<CardContent className='flex flex-col gap-4'>
				{resourceType.fields.length === 0 ? (
					<p className='text-muted-foreground text-sm'>No custom fields.</p>
				) : (
					<ul className='flex flex-wrap gap-2'>
						{resourceType.fields.map((field) => (
							<li key={field.key}>
								<Badge variant='outline'>
									{field.label} ({field.type}
									{field.required ? ', required' : ''})
								</Badge>
							</li>
						))}
					</ul>
				)}

				<div className='flex flex-col gap-2 border-t pt-4'>
					<p className='text-sm font-medium'>Resources</p>
					{resourcesQuery.isPending && <Skeleton className='h-10 w-full' />}
					{resourcesQuery.error && (
						<p className='text-destructive text-sm'>
							Couldn't load resources (
							{resourcesQuery.error instanceof ApiError
								? resourcesQuery.error.code
								: 'UNKNOWN_ERROR'}
							).
						</p>
					)}
					{resourcesQuery.data?.data.length === 0 && (
						<p className='text-muted-foreground text-sm'>No resources yet.</p>
					)}
					{resourcesQuery.data?.data.map((resource) => (
						<p key={resource.id} className='text-sm'>
							{resource.label}
						</p>
					))}
				</div>

				{adding ? (
					<div className='flex flex-col gap-3 border-t pt-4'>
						<div className='space-y-1'>
							<Label htmlFor={`resource-label-${resourceType.id}`}>Label</Label>
							<Input
								id={`resource-label-${resourceType.id}`}
								value={label}
								onChange={(e) => setLabel(e.target.value)}
								placeholder='Phone Booth 4'
							/>
						</div>

						<CustomFieldValuesEditor
							fields={resourceType.fields}
							values={values}
							onChange={setValues}
						/>

						{createResource.error && (
							<p className='text-destructive text-sm'>
								Couldn't create the resource (
								{createResource.error instanceof ApiError
									? createResource.error.code
									: 'UNKNOWN_ERROR'}
								).
							</p>
						)}

						<div className='flex gap-2'>
							<Button
								type='button'
								onClick={handleCreate}
								disabled={!label.trim() || createResource.isPending}
							>
								{createResource.isPending ? 'Creating…' : 'Create resource'}
							</Button>
							<Button
								type='button'
								variant='ghost'
								onClick={() => {
									setAdding(false);
									resetForm();
								}}
							>
								Cancel
							</Button>
						</div>
					</div>
				) : (
					<Button type='button' variant='outline' onClick={() => setAdding(true)}>
						Add resource
					</Button>
				)}
			</CardContent>
		</Card>
	);
}
