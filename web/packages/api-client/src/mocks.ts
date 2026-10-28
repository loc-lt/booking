import { bookingsScenarioHandlers, resourceTypesScenarioHandlers } from './scenarios';

// Resource types, resources, availability and bookings use the stateful
// scenario handlers, not the generated random/canned ones, so creating a
// resource type and then booking against it actually reflects it. See
// docs/frontend.md's "Mocks" section.
export const handlers = [...resourceTypesScenarioHandlers, ...bookingsScenarioHandlers];
