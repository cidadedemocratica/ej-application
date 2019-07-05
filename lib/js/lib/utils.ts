export const DEBUG = true;
export const DEVELOPMENT = DEBUG;


/**
 * Prints a warning in production via console.log() and throws an error in
 * development;
 */
export function warn(...args) {
    if (DEVELOPMENT) {
        let msg = args.join(', ');
        throw `[error] ${msg}`
    } else {
        console.log('[warning]', ...args);
    }
}

/**
 * Prints a message when in debug mode;
 */
export function debug(...args) {
    DEBUG ? console.log('[debug] ', ...args) : null;
}


//==============================================================================
// STRING FUNCTIONS
//==============================================================================

/**
 * Convert camelCase to dash-case.
 */
export function camelCaseToDash(myStr) {
    return myStr.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
}
