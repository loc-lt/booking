import { useHotkey } from '@tanstack/react-hotkeys';
import { cn } from 'cn';
import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card';

export type GuidedTourStep = {
	content: ReactNode;
	id: string;
	/** Runs once, the moment this step becomes active — e.g. to seed page state the step needs to point at. */
	onEnter?: () => void;
	/** CSS selector for the element to spotlight, or `null` to dim the whole page and center the card. */
	target: string | null;
	title: ReactNode;
};

type Props = {
	/** Defaults to `"Back"`. */
	backLabel?: string;
	/** Defaults to `"Finish"`. */
	finishLabel?: string;
	/** Defaults to `"Next"`. */
	nextLabel?: string;
	onOpenChange: (open: boolean) => void;
	open: boolean;
	/** Defaults to `"Skip"`. */
	skipLabel?: string;
	/** Defaults to `(current, total) => \`${current} / ${total}\`` . */
	stepCounterLabel?: (current: number, total: number) => ReactNode;
	steps: GuidedTourStep[];
};

type Rect = { height: number; left: number; top: number; width: number };

const SPOTLIGHT_PADDING_PX = 8;
const CARD_MARGIN_PX = 16;
const CARD_WIDTH_PX = 320;
// No real measurement of the card exists yet at the point the position is
// computed (see the comment above `cardTop` below) — this is a deliberately
// generous estimate for this tour's short, controlled step copy, not a
// generic "any content" allowance.
const ESTIMATED_CARD_HEIGHT_PX = 220;
const MEASURE_MAX_ATTEMPTS = 20;
const MEASURE_RETRY_MS = 50;

function measureRect(target: string): Rect | null {
	const element = document.querySelector(target);

	if (!element) {
		return null;
	}

	element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
	const rect = element.getBoundingClientRect();
	return { height: rect.height, left: rect.left, top: rect.top, width: rect.width };
}

function clamp(value: number, min: number, max: number): number {
	return Math.min(Math.max(value, min), max);
}

/**
 * A step-by-step spotlight tour: dims the page, cuts a highlighted hole
 * around each step's target element (or centers the card when there's no
 * target), and walks forward/back through `steps` with Skip/Escape to bail
 * out early. Portals to `document.body` and sits at `z-[100]` — every other
 * overlay in this package (Dialog/Tooltip/Select/Popover) is `z-50`, so a
 * tour that has to sit above all of them needs a clean margin past that
 * ceiling.
 */
export function GuidedTour({
	backLabel = 'Back',
	finishLabel = 'Finish',
	nextLabel = 'Next',
	onOpenChange,
	open,
	skipLabel = 'Skip',
	stepCounterLabel = (current, total) => `${current} / ${total}`,
	steps,
}: Props) {
	const [stepIndex, setStepIndex] = useState(0);
	const [targetRect, setTargetRect] = useState<Rect | null>(null);
	const enteredStepIdRef = useRef<string | null>(null);
	const nextButtonRef = useRef<HTMLButtonElement>(null);

	const step = steps[stepIndex];
	const isFirstStep = stepIndex === 0;
	const isLastStep = stepIndex === steps.length - 1;

	// Reset to the first step every time the tour (re)opens.
	useEffect(() => {
		if (open) {
			setStepIndex(0);
			enteredStepIdRef.current = null;
		}
	}, [open]);

	// Run the current step's `onEnter` exactly once per step activation, then
	// measure its target — retrying a few frames in case `onEnter` triggered
	// state elsewhere in the app whose DOM node isn't mounted on this tick yet.
	useLayoutEffect(() => {
		if (!open || !step) {
			return;
		}

		if (enteredStepIdRef.current !== step.id) {
			enteredStepIdRef.current = step.id;
			step.onEnter?.();
		}

		if (!step.target) {
			setTargetRect(null);
			return;
		}

		let cancelled = false;
		let attempts = 0;
		const target = step.target;

		const attemptMeasure = () => {
			if (cancelled) {
				return;
			}

			const rect = measureRect(target);

			if (rect) {
				setTargetRect(rect);
				return;
			}

			attempts += 1;
			if (attempts < MEASURE_MAX_ATTEMPTS) {
				window.setTimeout(attemptMeasure, MEASURE_RETRY_MS);
			} else {
				setTargetRect(null);
			}
		};

		attemptMeasure();

		return () => {
			cancelled = true;
		};
	}, [open, step]);

	// Keep the spotlight aligned with its target across layout changes while a
	// step is active.
	useEffect(() => {
		if (!open || !step?.target) {
			return;
		}

		const target = step.target;
		const remeasure = () => {
			const rect = measureRect(target);
			if (rect) {
				setTargetRect(rect);
			}
		};

		window.addEventListener('resize', remeasure);
		window.addEventListener('scroll', remeasure, true);

		return () => {
			window.removeEventListener('resize', remeasure);
			window.removeEventListener('scroll', remeasure, true);
		};
	}, [open, step]);

	useEffect(() => {
		if (open) {
			nextButtonRef.current?.focus();
		}
	}, [open]);

	useHotkey(
		'Escape',
		() => {
			if (open) {
				onOpenChange(false);
			}
		},
		{
			conflictBehavior: 'allow',
			preventDefault: true,
			requireReset: true,
		},
	);

	if (!open || !step) {
		return null;
	}

	const handleNext = () => {
		if (isLastStep) {
			onOpenChange(false);
		} else {
			setStepIndex((index) => index + 1);
		}
	};

	const handleBack = () => setStepIndex((index) => Math.max(index - 1, 0));
	const handleSkip = () => onOpenChange(false);

	const padded = targetRect
		? {
				height: targetRect.height + SPOTLIGHT_PADDING_PX * 2,
				left: targetRect.left - SPOTLIGHT_PADDING_PX,
				top: targetRect.top - SPOTLIGHT_PADDING_PX,
				width: targetRect.width + SPOTLIGHT_PADDING_PX * 2,
			}
		: null;

	// The card's actual size isn't known until it renders, so this positions
	// it from an estimated height (see the constant above) rather than a
	// measure-then-reposition pass — simpler, and accurate enough for this
	// tour's short, fixed-length step copy.
	const viewportWidth = window.innerWidth;
	const viewportHeight = window.innerHeight;

	const cardTop = padded
		? viewportHeight - (padded.top + padded.height) >= ESTIMATED_CARD_HEIGHT_PX + CARD_MARGIN_PX ||
			viewportHeight - (padded.top + padded.height) >= padded.top
			? padded.top + padded.height + CARD_MARGIN_PX
			: Math.max(padded.top - ESTIMATED_CARD_HEIGHT_PX - CARD_MARGIN_PX, CARD_MARGIN_PX)
		: undefined;
	const cardLeft = padded
		? clamp(
				padded.left + padded.width / 2 - CARD_WIDTH_PX / 2,
				CARD_MARGIN_PX,
				viewportWidth - CARD_WIDTH_PX - CARD_MARGIN_PX,
			)
		: undefined;

	return createPortal(
		<div aria-modal='true' className='fixed inset-0 z-[100]' role='dialog'>
			{padded ? (
				<>
					{/* Click-blocking only, kept sharp-cornered and invisible — the
					 * rounded dark backdrop below is purely visual and doesn't
					 * hit-test, so these strips are what actually stop clicks
					 * from reaching the dimmed page underneath. */}
					<div className='fixed inset-x-0 top-0' style={{ height: Math.max(padded.top, 0) }} />
					<div className='fixed inset-x-0 bottom-0' style={{ top: padded.top + padded.height }} />
					<div
						className='fixed'
						style={{
							height: padded.height,
							left: 0,
							top: padded.top,
							width: Math.max(padded.left, 0),
						}}
					/>
					<div
						className='fixed'
						style={{
							height: padded.height,
							left: padded.left + padded.width,
							right: 0,
							top: padded.top,
						}}
					/>
					{/* The visible dimming: a box-shadow spread around a rounded,
					 * transparent box gives the cutout the same rounded corners as
					 * the ring below, instead of the sharp corners a plain 4-strip
					 * backdrop would leave showing through it. */}
					<div
						className='pointer-events-none fixed rounded-lg'
						style={{
							boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.6)',
							height: padded.height,
							left: padded.left,
							top: padded.top,
							width: padded.width,
						}}
					/>
					<div
						className='ring-primary pointer-events-none fixed rounded-lg ring-2'
						data-testid='guided-tour-spotlight'
						style={{
							height: padded.height,
							left: padded.left,
							top: padded.top,
							width: padded.width,
						}}
					/>
				</>
			) : (
				<div className='fixed inset-0 bg-black/60' />
			)}

			<Card
				className={cn(
					'fixed w-[320px] shadow-lg',
					!padded && 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2',
				)}
				style={padded ? { left: cardLeft, top: cardTop } : undefined}
			>
				<CardHeader>
					<CardTitle>{step.title}</CardTitle>
				</CardHeader>
				<CardContent>
					<CardDescription>{step.content}</CardDescription>
				</CardContent>
				<CardFooter className='justify-between'>
					<Button onClick={handleSkip} type='button' variant='ghost'>
						{skipLabel}
					</Button>
					<div className='flex items-center gap-2'>
						<span className='text-muted-foreground text-xs'>
							{stepCounterLabel(stepIndex + 1, steps.length)}
						</span>
						{isFirstStep ? null : (
							<Button onClick={handleBack} type='button' variant='outline'>
								{backLabel}
							</Button>
						)}
						<Button onClick={handleNext} ref={nextButtonRef} type='button'>
							{isLastStep ? finishLabel : nextLabel}
						</Button>
					</div>
				</CardFooter>
			</Card>
		</div>,
		document.body,
	);
}
