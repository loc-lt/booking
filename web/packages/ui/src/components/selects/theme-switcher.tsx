import { Monitor, Moon, Sun } from 'lucide-react';
import { Icon } from '../common/icon';
import { Button } from '../ui/button';
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from '../ui/dropdown-menu';

export type ThemeOption = 'light' | 'dark' | 'system';

const THEME_ICONS: Record<ThemeOption, typeof Sun> = {
	dark: Moon,
	light: Sun,
	system: Monitor,
};

export interface ThemeSwitcherLabels {
	trigger: string;
	light: string;
	dark: string;
	system: string;
}

const DEFAULT_LABELS: ThemeSwitcherLabels = {
	dark: 'Dark',
	light: 'Light',
	system: 'System',
	trigger: 'Toggle theme',
};

export interface ThemeSwitcherProps {
	theme: ThemeOption;
	onThemeChange: (theme: ThemeOption) => void;
	labels?: Partial<ThemeSwitcherLabels>;
}

/**
 * Controlled light/dark/system select — pairs with `@booking-core/app-kit`'s
 * `useTheme()`, or any other state you manage yourself.
 */
export function ThemeSwitcher({ theme, onThemeChange, labels }: ThemeSwitcherProps) {
	const mergedLabels = { ...DEFAULT_LABELS, ...labels };
	const CurrentIcon = THEME_ICONS[theme];

	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				render={
					<Button
						aria-label={mergedLabels.trigger}
						className='gap-2'
						type='button'
						variant='outline'
					>
						<CurrentIcon className='size-4' />
					</Button>
				}
			/>
			<DropdownMenuContent align='end' className='w-36'>
				{(Object.keys(THEME_ICONS) as ThemeOption[]).map((option) => {
					const OptionIcon = THEME_ICONS[option];
					const isSelected = option === theme;

					return (
						<DropdownMenuItem
							aria-checked={isSelected}
							key={option}
							onClick={() => onThemeChange(option)}
							role='menuitemradio'
						>
							<OptionIcon className='size-4' />
							<span>{mergedLabels[option]}</span>
							{isSelected ? <Icon className='ml-auto' name='Check' /> : null}
						</DropdownMenuItem>
					);
				})}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
