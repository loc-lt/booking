import { Component, type ReactNode } from 'react';
import { captureError } from './tracking';

interface Props {
	children: ReactNode;
}

interface State {
	error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
	state: State = { error: null };

	static getDerivedStateFromError(error: Error): State {
		return { error };
	}

	componentDidCatch(error: Error): void {
		captureError(error);
	}

	render() {
		if (this.state.error) {
			return (
				<div className='flex min-h-dvh flex-col items-center justify-center gap-2 p-8 text-center'>
					<h1 className='text-lg font-semibold'>Something went wrong</h1>
					<p className='text-muted-foreground text-sm'>
						Try reloading the page. If it keeps happening, tell the team what you were doing.
					</p>
				</div>
			);
		}

		return this.props.children;
	}
}
