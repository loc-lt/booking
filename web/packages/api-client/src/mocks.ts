import {
	getCreateResourceTypeMockHandler,
	getGetResourceTypeMockHandler,
	getListResourceTypesMockHandler,
} from './generated/endpoints/resource-types/resource-types.msw';
import {
	getCreateResourceMockHandler,
	getGetResourceMockHandler,
	getListResourcesMockHandler,
} from './generated/endpoints/resources/resources.msw';

export const handlers = [
	getListResourceTypesMockHandler(),
	getCreateResourceTypeMockHandler(),
	getGetResourceTypeMockHandler(),
	getListResourcesMockHandler(),
	getCreateResourceMockHandler(),
	getGetResourceMockHandler(),
];
