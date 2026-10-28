import type { FieldDefinition } from '@booking-core/api-client';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { CustomFieldValueInput } from './CustomFieldValueInput';

function field(overrides: Partial<FieldDefinition>): FieldDefinition {
	return { key: 'f', label: 'F', type: 'text', ...overrides };
}

/** Wires CustomFieldValueInput to real state so a controlled input reflects each keystroke. */
function Harness({
	field: fieldDefinition,
	onChange,
}: {
	field: FieldDefinition;
	onChange: (value: unknown) => void;
}) {
	const [value, setValue] = useState<unknown>(undefined);
	return (
		<CustomFieldValueInput
			id='f'
			field={fieldDefinition}
			value={value}
			onChange={(next) => {
				setValue(next);
				onChange(next);
			}}
		/>
	);
}

describe('CustomFieldValueInput', () => {
	it('toggles a boolean field and reports a boolean, not a string', async () => {
		const user = userEvent.setup();
		const onChange = vi.fn();
		render(
			<CustomFieldValueInput
				id='f'
				field={field({ type: 'boolean' })}
				value={false}
				onChange={onChange}
			/>,
		);

		await user.click(screen.getByRole('checkbox'));

		expect(onChange).toHaveBeenCalledWith(true);
	});

	it('reports a number, not a string, for an integer field', async () => {
		const user = userEvent.setup();
		const onChange = vi.fn();
		render(<Harness field={field({ type: 'integer' })} onChange={onChange} />);

		await user.type(screen.getByRole('spinbutton'), '42');

		expect(onChange).toHaveBeenLastCalledWith(42);
		for (const call of onChange.mock.calls) {
			expect(typeof call[0]).toBe('number');
		}
	});

	it('reports the option value when a select option is chosen', async () => {
		const user = userEvent.setup();
		const onChange = vi.fn();
		const selectField = field({
			type: 'select',
			options: [
				{ value: 'small', label: 'Small' },
				{ value: 'large', label: 'Large' },
			],
		});
		render(
			<CustomFieldValueInput id='f' field={selectField} value={undefined} onChange={onChange} />,
		);

		await user.click(screen.getByRole('combobox'));
		await user.click(await screen.findByRole('option', { name: 'Large' }));

		expect(onChange).toHaveBeenCalledWith('large');
	});

	it('falls back to a plain text input for a type with no dedicated control', () => {
		render(
			<CustomFieldValueInput
				id='f'
				field={field({ type: 'reference' })}
				value={undefined}
				onChange={() => {}}
			/>,
		);

		expect(screen.getByPlaceholderText('reference — enter raw value')).toBeTruthy();
	});
});
