import type { FieldDefinition } from '@booking-core/api-client';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { FieldDefinitionsEditor, type ResourceTypeOption } from './FieldDefinitionsEditor';

function Harness({
	initial,
	resourceTypeOptions = [],
}: {
	initial: FieldDefinition[];
	resourceTypeOptions?: ResourceTypeOption[];
}) {
	const [value, setValue] = useState(initial);
	return (
		<div>
			<FieldDefinitionsEditor
				value={value}
				onChange={setValue}
				resourceTypeOptions={resourceTypeOptions}
			/>
			<pre data-testid='value'>{JSON.stringify(value)}</pre>
		</div>
	);
}

function currentFields(): FieldDefinition[] {
	return JSON.parse(screen.getByTestId('value').textContent ?? '[]');
}

async function selectFieldType(user: ReturnType<typeof userEvent.setup>, optionLabel: string) {
	await user.click(screen.getByLabelText('Type'));
	await user.click(await screen.findByRole('option', { name: optionLabel }));
}

describe('FieldDefinitionsEditor', () => {
	it('shows the validation inputs for the field’s current type', async () => {
		const user = userEvent.setup();
		render(<Harness initial={[{ key: 'k', label: 'K', type: 'text', required: false }]} />);

		expect(screen.getByText('Min length')).toBeTruthy();
		expect(screen.getByText('Pattern')).toBeTruthy();
		expect(screen.queryByText('Multiple of')).toBeNull();

		await selectFieldType(user, 'Integer');

		expect(screen.getByText('Multiple of')).toBeTruthy();
		expect(screen.queryByText('Pattern')).toBeNull();
	});

	it('shows no validation inputs for a type that takes none', () => {
		render(<Harness initial={[{ key: 'k', label: 'K', type: 'boolean', required: false }]} />);

		expect(screen.queryByText('Min length')).toBeNull();
		expect(screen.queryByText('Min')).toBeNull();
		expect(screen.queryByText('Min items')).toBeNull();
	});

	it('clears options when switching a field away from select', async () => {
		const user = userEvent.setup();
		render(
			<Harness
				initial={[
					{
						key: 'k',
						label: 'K',
						type: 'select',
						required: false,
						options: [{ value: 'a', label: 'A' }],
					},
				]}
			/>,
		);

		await selectFieldType(user, 'Integer');

		expect(currentFields()[0]?.options).toBeUndefined();
	});

	it('clears validation when switching to a type with a different validation kind', async () => {
		const user = userEvent.setup();
		render(
			<Harness
				initial={[
					{
						key: 'k',
						label: 'K',
						type: 'text',
						required: false,
						validation: { pattern: '^[A-Z]+$' },
					},
				]}
			/>,
		);

		await selectFieldType(user, 'Yes / no');

		expect(currentFields()[0]?.validation).toBeUndefined();
	});

	it('sets the target resource type when one is chosen for a reference field', async () => {
		const user = userEvent.setup();
		render(
			<Harness
				initial={[{ key: 'k', label: 'K', type: 'reference', required: false }]}
				resourceTypeOptions={[{ value: 'table-type', label: 'Table' }]}
			/>,
		);

		await user.click(screen.getByLabelText('References'));
		await user.click(await screen.findByRole('option', { name: 'Table' }));

		expect(currentFields()[0]?.validation?.targetResourceTypeId).toBe('table-type');
	});

	it('clears the target resource type when switching a field away from reference', async () => {
		const user = userEvent.setup();
		render(
			<Harness
				initial={[
					{
						key: 'k',
						label: 'K',
						type: 'reference',
						required: false,
						validation: { targetResourceTypeId: 'table-type' },
					},
				]}
				resourceTypeOptions={[{ value: 'table-type', label: 'Table' }]}
			/>,
		);

		await selectFieldType(user, 'Integer');

		expect(currentFields()[0]?.validation).toBeUndefined();
	});

	it('asks for another resource type first when none exist yet for a reference field to target', () => {
		render(<Harness initial={[{ key: 'k', label: 'K', type: 'reference', required: false }]} />);

		expect(screen.getByText(/Create another resource type first/)).toBeTruthy();
		expect(screen.queryByLabelText('References')).toBeNull();
	});
});
