import { CreateResourceTypeForm } from './CreateResourceTypeForm';
import { ResourceTypesList } from './ResourceTypesList';

export function ResourceTypesPage() {
	return (
		<div className='mx-auto flex max-w-3xl flex-col gap-6 p-6'>
			<h1 className='text-xl font-semibold'>Resource types</h1>
			<CreateResourceTypeForm />
			<ResourceTypesList />
		</div>
	);
}
