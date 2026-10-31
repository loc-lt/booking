import { zodResolver } from '@hookform/resolvers/zod';
import { cn } from 'cn';
import { useEffect } from 'react';
import { Controller, type DefaultValues, type Path, type Resolver, useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { ClearableSelect } from './clearable-select';
import { DatePicker } from './date-picker';
import { DateTimePicker } from './date-time-picker';
import { Icon } from './icon';
import { Search } from './search';
import type { DataTableFilterField, FilterValues } from './types';

const dataTableFiltersSchema = z.record(z.string(), z.string());
const dataTableFiltersResolver = zodResolver(dataTableFiltersSchema);

type Props<TFilters extends FilterValues> = {
	applyLabel: string;
	className?: string;
	clearLabel: string;
	fields: readonly DataTableFilterField<TFilters>[];
	gridClassName?: string;
	onReset?: () => void;
	onSubmit?: () => void;
	onValueChange: <TName extends keyof TFilters & string>(
		name: TName,
		value: TFilters[TName],
	) => void;
	resetLabel: string;
	submitLabel: string;
	values: TFilters;
};

export function DataTableFilters<TFilters extends FilterValues>({
	applyLabel,
	className,
	clearLabel,
	fields,
	gridClassName,
	onReset,
	onSubmit,
	onValueChange,
	resetLabel,
	submitLabel,
	values,
}: Props<TFilters>) {
	const { control, handleSubmit, reset } = useForm<TFilters>({
		defaultValues: values as DefaultValues<TFilters>,
		resolver: dataTableFiltersResolver as unknown as Resolver<TFilters>,
		values,
	});

	useEffect(() => {
		reset(values);
	}, [reset, values]);

	const handleFieldValueChange = <TName extends keyof TFilters & string>(
		name: TName,
		value: string,
	) => {
		onValueChange(name, value as TFilters[TName]);
	};

	return (
		<form className={cn('space-y-3', className)} onSubmit={handleSubmit(() => onSubmit?.())}>
			<div className={cn('min-w-0', gridClassName ?? 'grid gap-3 sm:grid-cols-2 xl:grid-cols-4')}>
				{fields.map((field) => {
					const value = values[field.name];

					return (
						<div className={cn('min-w-0 space-y-1.5', field.className)} key={field.name}>
							<Label htmlFor={field.name}>{field.label}</Label>

							<Controller
								control={control}
								name={field.name as Path<TFilters>}
								render={({ field: controllerField }) => {
									if (field.type === 'select') {
										return (
											<ClearableSelect
												clearLabel={clearLabel}
												disabled={field.disabled}
												emptyLabel={field.emptyLabel}
												id={field.name}
												onValueChange={(nextValue) => {
													controllerField.onChange(nextValue);
													handleFieldValueChange(field.name, nextValue);
												}}
												options={field.options}
												value={value || ''}
											/>
										);
									}

									if (field.type === 'datetime') {
										return (
											<DateTimePicker
												clearLabel={clearLabel}
												defaultTime={field.defaultTime}
												disabled={field.disabled}
												id={field.name}
												onValueChange={(nextValue) => {
													controllerField.onChange(nextValue);
													handleFieldValueChange(field.name, nextValue);
												}}
												placeholder={field.placeholder}
												submitLabel={applyLabel}
												value={value || ''}
											/>
										);
									}

									if (field.type === 'date') {
										return (
											<DatePicker
												clearLabel={clearLabel}
												disabled={field.disabled}
												id={field.name}
												onValueChange={(nextValue) => {
													controllerField.onChange(nextValue);
													handleFieldValueChange(field.name, nextValue);
												}}
												placeholder={field.placeholder}
												submitLabel={applyLabel}
												value={value || ''}
											/>
										);
									}

									return (
										<Search
											clearLabel={clearLabel}
											disabled={field.disabled}
											id={field.name}
											onValueChange={(nextValue) => {
												controllerField.onChange(nextValue);
												handleFieldValueChange(field.name, nextValue);
											}}
											placeholder={field.placeholder}
											value={value}
										/>
									);
								}}
							/>
						</div>
					);
				})}
			</div>

			<div className='flex flex-wrap justify-end gap-2'>
				<Button onClick={onReset} type='button' variant='outline'>
					<Icon name='BrushCleaning' />
					{resetLabel}
				</Button>
				<Button type='submit' variant='outline'>
					<Icon name='Search' />
					{submitLabel}
				</Button>
			</div>
		</form>
	);
}
