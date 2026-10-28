import { resourceTypesScenarioHandlers } from './scenarios';

// Resource types and resources use the stateful scenario handlers, not the
// generated random/canned ones, so creating a resource type and then listing
// resources actually reflects it. See docs/frontend.md's "Mocks" section.
export const handlers = [...resourceTypesScenarioHandlers];
