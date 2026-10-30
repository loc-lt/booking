import { createServer } from 'node:http';
import {
	approveOp,
	cancelOp,
	checkInOp,
	createBookingOp,
	createResourceOp,
	createResourceTypeOp,
	getBookingOp,
	getResourceOp,
	getResourceTypeOp,
	listBookingsOp,
	listResourcesOp,
	listResourceTypesOp,
	rejectOp,
	resetBookingsState,
	resetResourceTypesState,
	searchAvailabilityOp,
	updateResourceTypeOp,
} from '@booking-core/api-client';

// Runs the same demo "backend" logic as each app's in-browser MSW mocks
// (web/packages/api-client/src/scenarios/*Operations.ts), but as one real HTTP
// server both apps can point at — so creating a resource type in console,
// booking it in member, and approving it back in console all see the same
// state. See docs/frontend.md's "Mocks" section.

const PORT = Number(process.env.PORT ?? 4000);

const ROUTES = [
	{ method: 'GET', pattern: /^\/resource-types$/, handler: () => listResourceTypesOp() },
	{ method: 'POST', pattern: /^\/resource-types$/, handler: (ctx) => createResourceTypeOp(ctx.body) },
	{
		method: 'GET',
		pattern: /^\/resource-types\/([^/]+)$/,
		handler: (_ctx, [id]) => getResourceTypeOp(id),
	},
	{
		method: 'PATCH',
		pattern: /^\/resource-types\/([^/]+)$/,
		handler: (ctx, [id]) => updateResourceTypeOp(id, ctx.body),
	},
	{
		method: 'GET',
		pattern: /^\/resources$/,
		handler: (ctx) =>
			listResourcesOp({
				resourceTypeId: ctx.query.get('resourceTypeId'),
				siteId: ctx.query.get('siteId'),
			}),
	},
	{ method: 'POST', pattern: /^\/resources$/, handler: (ctx) => createResourceOp(ctx.body) },
	{ method: 'GET', pattern: /^\/resources\/([^/]+)$/, handler: (_ctx, [id]) => getResourceOp(id) },
	{
		method: 'GET',
		pattern: /^\/availability$/,
		handler: (ctx) =>
			searchAvailabilityOp({
				siteId: ctx.query.get('siteId'),
				resourceTypeId: ctx.query.get('resourceTypeId'),
				resourceId: ctx.query.get('resourceId'),
				date: ctx.query.get('date'),
			}),
	},
	{
		method: 'GET',
		pattern: /^\/bookings$/,
		handler: (ctx) =>
			listBookingsOp({
				resourceId: ctx.query.get('resourceId'),
				resourceTypeId: ctx.query.get('resourceTypeId'),
				siteId: ctx.query.get('siteId'),
				memberId: ctx.query.get('memberId'),
				status: ctx.query.get('status'),
			}),
	},
	{ method: 'POST', pattern: /^\/bookings$/, handler: (ctx) => createBookingOp(ctx.body) },
	{ method: 'GET', pattern: /^\/bookings\/([^/]+)$/, handler: (_ctx, [id]) => getBookingOp(id) },
	{
		method: 'POST',
		pattern: /^\/bookings\/([^/]+)\/check-in$/,
		handler: (_ctx, [id]) => checkInOp(id),
	},
	{ method: 'POST', pattern: /^\/bookings\/([^/]+)\/cancel$/, handler: (_ctx, [id]) => cancelOp(id) },
	{
		method: 'POST',
		pattern: /^\/bookings\/([^/]+)\/approve$/,
		handler: (_ctx, [id]) => approveOp(id),
	},
	{
		method: 'POST',
		pattern: /^\/bookings\/([^/]+)\/reject$/,
		handler: (ctx, [id]) => rejectOp(id, ctx.body),
	},
	{
		method: 'POST',
		pattern: /^\/__reset$/,
		handler: () => {
			resetResourceTypesState();
			resetBookingsState();
			return { status: 204, body: undefined };
		},
	},
];

const CORS_HEADERS = {
	'Access-Control-Allow-Origin': '*',
	'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
	'Access-Control-Allow-Headers': 'Content-Type, X-Tenant-Id, Authorization, Idempotency-Key',
};

async function readJsonBody(req) {
	const chunks = [];
	for await (const chunk of req) {
		chunks.push(chunk);
	}
	if (chunks.length === 0) {
		return undefined;
	}
	return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}

const server = createServer(async (req, res) => {
	if (req.method === 'OPTIONS') {
		res.writeHead(204, CORS_HEADERS);
		res.end();
		return;
	}

	const url = new URL(req.url ?? '/', `http://${req.headers.host ?? 'localhost'}`);
	const route = ROUTES.find((r) => r.method === req.method && r.pattern.test(url.pathname));

	if (!route) {
		res.writeHead(404, { ...CORS_HEADERS, 'Content-Type': 'application/json' });
		res.end(JSON.stringify({ code: 'NOT_FOUND', detail: `No route for ${req.method} ${url.pathname}` }));
		return;
	}

	try {
		const body = await readJsonBody(req);
		const match = route.pattern.exec(url.pathname);
		const { status, body: responseBody } = route.handler({ query: url.searchParams, body }, match.slice(1));

		res.writeHead(status, { ...CORS_HEADERS, 'Content-Type': 'application/json' });
		res.end(responseBody === undefined ? undefined : JSON.stringify(responseBody));
	} catch (error) {
		console.error(error);
		res.writeHead(500, { ...CORS_HEADERS, 'Content-Type': 'application/json' });
		res.end(JSON.stringify({ code: 'UNKNOWN_ERROR', detail: String(error) }));
	}
});

server.listen(PORT, () => {
	console.log(`Shared mock backend listening on http://localhost:${PORT}`);
	console.log('Point both apps\' public/config.js at this URL with apiMode: "real".');
});
