import type { FieldDefinition } from '@booking-core/api-client';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { CustomFieldValuesEditor } from './CustomFieldValuesEditor';

const referenceField: FieldDefinition = {
	key: 'primary_table',
	label: 'Primary table',
	type: 'reference',
	validation: { targetResourceTypeId: 'table-type' },
};

describe('CustomFieldValuesEditor', () => {
	it('passes referenceOptions through to a non-boolean field, like a reference field', async () => {
		const user = userEvent.setup();
		const onChange = vi.fn();
		render(
			<CustomFieldValuesEditor
				fields={[referenceField]}
				values={{}}
				onChange={onChange}
				referenceOptions={{ 'table-type': [{ value: 'table-a', label: 'Table A' }] }}
			/>,
		);

		await user.click(screen.getByRole('combobox'));
		await user.click(await screen.findByRole('option', { name: 'Table A' }));

		expect(onChange).toHaveBeenCalledWith({ primary_table: 'table-a' });
	});
});
