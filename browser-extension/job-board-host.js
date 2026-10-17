/* Shared by the popup and the isolated content script. */
(function () {
    'use strict';

    function jobBoardHostMatches(value, domain) {
        try {
            const parsed = new URL(value);
            if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return false;
            const hostname = parsed.hostname.toLowerCase().replace(/\.$/, '');
            return hostname === domain || hostname.endsWith('.' + domain);
        } catch {
            return false;
        }
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = jobBoardHostMatches;
    } else {
        globalThis.jobBoardHostMatches = jobBoardHostMatches;
    }
})();
