import { createFileRoute, Link } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
	component: Index,
});

function Index() {
	return (
		<div className='p-6'>
			<Link to='/resource-types' className='text-sm hover:underline'>
				Go to resource types →
			</Link>
		</div>
	);
}
