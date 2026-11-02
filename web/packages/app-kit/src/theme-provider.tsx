import {
	createContext,
	type ReactNode,
	useCallback,
	useContext,
	useEffect,
	useMemo,
	useState,
} from 'react';

export type Theme = 'light' | 'dark' | 'system';

export interface ThemeProviderProps {
	children: ReactNode;
	/** Theme used before anything is stored, and whenever storage is unreadable. Defaults to `"system"`. */
	defaultTheme?: Theme;
	/** `localStorage` key the chosen theme is persisted under. */
	storageKey?: string;
}

interface ThemeContextValue {
	theme: Theme;
	setTheme: (theme: Theme) => void;
}

export const DEFAULT_THEME_STORAGE_KEY = 'booking-core-theme';

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const DARK_MEDIA_QUERY = '(prefers-color-scheme: dark)';

function getSystemTheme(): 'light' | 'dark' {
	return window.matchMedia(DARK_MEDIA_QUERY).matches ? 'dark' : 'light';
}

function readStoredTheme(storageKey: string, fallback: Theme): Theme {
	const stored = window.localStorage.getItem(storageKey);
	return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : fallback;
}

/**
 * Applies a light/dark/system theme by toggling the `dark` class on
 * `<html>`, matching `@custom-variant dark` in `@booking-core/ui`'s
 * stylesheet. Persists the choice to `localStorage` and follows the OS
 * setting live while `theme` is `"system"`.
 */
export function ThemeProvider({
	children,
	defaultTheme = 'system',
	storageKey = DEFAULT_THEME_STORAGE_KEY,
}: ThemeProviderProps) {
	const [theme, setThemeState] = useState<Theme>(() => readStoredTheme(storageKey, defaultTheme));

	useEffect(() => {
		const root = document.documentElement;
		const applyResolvedTheme = () => {
			const resolved = theme === 'system' ? getSystemTheme() : theme;
			root.classList.toggle('dark', resolved === 'dark');
		};

		applyResolvedTheme();

		if (theme !== 'system') {
			return undefined;
		}

		const media = window.matchMedia(DARK_MEDIA_QUERY);
		media.addEventListener('change', applyResolvedTheme);

		return () => {
			media.removeEventListener('change', applyResolvedTheme);
		};
	}, [theme]);

	const setTheme = useCallback(
		(nextTheme: Theme) => {
			window.localStorage.setItem(storageKey, nextTheme);
			setThemeState(nextTheme);
		},
		[storageKey],
	);

	const value = useMemo(() => ({ setTheme, theme }), [theme, setTheme]);

	return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
	const context = useContext(ThemeContext);

	if (!context) {
		throw new Error('useTheme must be used within a ThemeProvider');
	}

	return context;
}
