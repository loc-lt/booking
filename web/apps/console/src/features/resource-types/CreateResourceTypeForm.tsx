import {
	ApiError,
	getListResourceTypesQueryKey,
	schemas,
	useCreateResourceType,
} from '@booking-core/api-client';
import { trackEvent } from '@booking-core/app-kit';
import { FieldDefinitionsEditor } from '@booking-core/custom-fields';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@booking-core/ui';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';

const formSchema = schemas.createResourceTypeBody.extend({
	key: z
		.string()
		.min(1, 'Key is required')
		.regex(
			/^[a-z][a-z0-9_]*$/,
			'Use lowercase letters, numbers and underscores, starting with a letter',
		),
	label: z.string().min(1, 'Label is required'),
});

type FormInput = z.input<typeof formSchema>;
type FormOutput = z.output<typeof formSchema>;

const defaultValues: FormInput = { key: '', label: '', fields: [] };

export function CreateResourceTypeForm() {
	const queryClient = useQueryClient();
	const {
		control,
		register,
		handleSubmit,
		reset,
		setError,
		formState: { errors, isSubmitting },
	} = useForm<FormInput, unknown, FormOutput>({
		resolver: zodResolver(formSchema),
		defaultValues,
	});
	const createResourceType = useCreateResourceType();

	const onSubmit = handleSubmit((values) => {
		createResourceType.mutate(
			{ data: values },
			{
				onSuccess: () => {
					trackEvent('resource_type_created', { fieldCount: values.fields.length });
					reset(defaultValues);
					queryClient.invalidateQueries({ queryKey: getListResourceTypesQueryKey() });
				},
				onError: (error) => {
					if (error instanceof ApiError && error.code === 'VALIDATION_FAILED') {
						const body = error.body as { errors?: { field: string; message: string }[] };
						for (const fieldError of body.errors ?? []) {
							if (fieldError.field === 'key' || fieldError.field === 'label') {
								setError(fieldError.field, { message: fieldError.message });
							}
						}
					}
				},
			},
		);
	});

	const topLevelError =
		createResourceType.error instanceof ApiError &&
		createResourceType.error.code !== 'VALIDATION_FAILED'
			? createResourceType.error.code
			: null;

	return (
		<Card>
			<CardHeader>
				<CardTitle>New resource type</CardTitle>
			</CardHeader>
			<CardContent>
				<form onSubmit={onSubmit} className='flex flex-col gap-4'>
					<div className='flex gap-4'>
						<div className='flex-1 space-y-1'>
							<Label htmlFor='label'>Label</Label>
							<Input id='label' placeholder='Phone booth' {...register('label')} />
							{errors.label && <p className='text-destructive text-sm'>{errors.label.message}</p>}
						</div>
						<div className='flex-1 space-y-1'>
							<Label htmlFor='key'>Key</Label>
							<Input id='key' placeholder='phone_booth' {...register('key')} />
							{errors.key && <p className='text-destructive text-sm'>{errors.key.message}</p>}
						</div>
					</div>

					<div className='space-y-1'>
						<Label>Custom fields</Label>
						<Controller
							control={control}
							name='fields'
							render={({ field }) => (
								<FieldDefinitionsEditor value={field.value ?? []} onChange={field.onChange} />
							)}
						/>
					</div>

					{topLevelError && (
						<p className='text-destructive text-sm'>
							Couldn't create the resource type ({topLevelError}). Try again.
						</p>
					)}

					<Button type='submit' disabled={isSubmitting || createResourceType.isPending}>
						{createResourceType.isPending ? 'Creating…' : 'Create resource type'}
					</Button>
				</form>
			</CardContent>
		</Card>
	);
}
