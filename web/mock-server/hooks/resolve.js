// @booking-core/api-client is built for bundlers (moduleResolution: "Bundler" —
// see web/tsconfig.base.json), so its compiled relative imports omit the `.js`
// extension plain Node ESM requires. This loader hook retries an unresolved
// relative specifier with `.js` appended, so this server can run it unmodified
// with plain `node`, without changing that package's build target.
export async function resolve(specifier, context, nextResolve) {
	try {
		return await nextResolve(specifier, context);
	} catch (error) {
		if (!specifier.startsWith('.')) {
			throw error;
		}
		if (error?.code === 'ERR_MODULE_NOT_FOUND') {
			return nextResolve(`${specifier}.js`, context);
		}
		if (error?.code === 'ERR_UNSUPPORTED_DIR_IMPORT') {
			return nextResolve(`${specifier}/index.js`, context);
		}
		throw error;
	}
}
