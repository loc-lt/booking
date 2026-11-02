import {
	ApiError,
	getListResourcesQueryKey,
	getListResourceTypesQueryKey,
	type ResourceType,
	useCreateResource,
	useListResources,
	useUpdateResourceType,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import {
	CustomFieldValuesEditor,
	FIELD_SCOPE_LABELS,
	fieldScope,
	isResourceScoped,
} from '@booking-core/custom-fields';
import {
	Badge,
	Button,
	Card,
	CardContent,
	CardHeader,
	CardTitle,
	ClearableInput,
	Label,
	Skeleton,
} from '@booking-core/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { FlowConfigFields } from './flow-config-fields';

// Sites aren't built yet, so new resources land at this fixed demo site.
const DEMO_SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';

export function ResourceTypeCard({ resourceType }: { resourceType: ResourceType }) {
	const queryClient = useQueryClient();
	const [adding, setAdding] = useState(false);
	const [label, setLabel] = useState('');
	const [values, setValues] = useState<Record<string, unknown>>({});
	const [editingFlowConfig, setEditingFlowConfig] = useState(false);
	const [flowConfigDraft, setFlowConfigDraft] = useState(resourceType.flowConfig);
	const createResource = useCreateResource();
	const updateResourceType = useUpdateResourceType();
	const resourcesQuery = useListResources({ resourceTypeId: resourceType.id });
	const allResourcesQuery = useListResources();
	const referenceOptions: Record<string, { value: string; label: string }[]> = {};
	for (const resource of allResourcesQuery.data?.data ?? []) {
		const existing = referenceOptions[resource.resourceTypeId] ?? [];
		existing.push({ value: resource.id, label: resource.label });
		referenceOptions[resource.resourceTypeId] = existing;
	}

	function startEditingFlowConfig() {
		setFlowConfigDraft(resourceType.flowConfig);
		setEditingFlowConfig(true);
	}

	function handleSaveFlowConfig() {
		updateResourceType.mutate(
			{
				resourceTypeId: resourceType.id,
				data: { baseVersion: resourceType.version, flowConfig: flowConfigDraft },
			},
			{
				onSuccess: () => {
					trackEvent('resource_type_flow_config_updated', {
						resourceTypeId: resourceType.id,
						confirmation: flowConfigDraft.confirmation,
					});
					setEditingFlowConfig(false);
					queryClient.invalidateQueries({ queryKey: getListResourceTypesQueryKey() });
				},
			},
		);
	}

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
									{field.required ? ', required' : ''}, {FIELD_SCOPE_LABELS[fieldScope(field)]})
								</Badge>
							</li>
						))}
					</ul>
				)}

				<div className='flex flex-col gap-3 border-t pt-4'>
					<div className='flex items-center justify-between'>
						<p className='text-sm font-medium'>Flow config</p>
						{!editingFlowConfig && (
							<Button type='button' size='sm' variant='outline' onClick={startEditingFlowConfig}>
								Edit flow config
							</Button>
						)}
					</div>

					{editingFlowConfig ? (
						<>
							<FlowConfigFields
								idPrefix={`resource-type-${resourceType.id}`}
								value={flowConfigDraft}
								onChange={setFlowConfigDraft}
							/>
							{updateResourceType.error && (
								<p className='text-destructive text-sm'>
									{updateResourceType.error instanceof ApiError &&
									updateResourceType.error.code === 'STALE_VERSION'
										? 'Someone else changed this resource type — reload to see their change.'
										: `Couldn't save the flow config (${
												updateResourceType.error instanceof ApiError
													? updateResourceType.error.code
													: 'UNKNOWN_ERROR'
											}).`}
								</p>
							)}
							<div className='flex gap-2'>
								<Button
									type='button'
									size='sm'
									onClick={handleSaveFlowConfig}
									disabled={updateResourceType.isPending}
								>
									{updateResourceType.isPending ? 'Saving…' : 'Save'}
								</Button>
								<Button
									type='button'
									size='sm'
									variant='ghost'
									onClick={() => setEditingFlowConfig(false)}
								>
									Cancel
								</Button>
							</div>
						</>
					) : (
						<Badge variant='outline'>{resourceType.flowConfig.confirmation}</Badge>
					)}
				</div>

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
							<ClearableInput
								id={`resource-label-${resourceType.id}`}
								clearLabel='Clear'
								onChange={(e) => setLabel(e.target.value)}
								onClear={() => setLabel('')}
								placeholder='Phone Booth 4'
								value={label}
							/>
						</div>

						<CustomFieldValuesEditor
							fields={resourceType.fields.filter(isResourceScoped)}
							values={values}
							onChange={setValues}
							referenceOptions={referenceOptions}
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
