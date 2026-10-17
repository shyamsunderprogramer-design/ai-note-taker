const test = require('node:test');
const assert = require('node:assert/strict');
const matches = require('../../browser-extension/job-board-host.js');

test('job board matching allows the real host and its subdomains', () => {
  for (const domain of ['linkedin.com', 'indeed.com', 'glassdoor.com', 'icims.com',
    'greenhouse.io', 'lever.co', 'workday.com', 'myworkday.com', 'ashbyhq.com']) {
    assert.equal(matches(`https://${domain}/jobs`, domain), true);
    assert.equal(matches(`https://jobs.${domain}/`, domain), true);
    assert.equal(matches(`https://${domain.toUpperCase()}./`, domain), true);
  }
});

test('job board matching rejects deceptive hosts, paths, credentials and schemes', () => {
  for (const value of ['https://notlinkedin.com', 'https://linkedin.com.evil.test',
    'https://evil.test/linkedin.com', 'https://evil.test/?next=linkedin.com',
    'https://linkedin.com@evil.test', 'https://linkedin.com%40evil.test',
    'ftp://linkedin.com', 'javascript:linkedin.com', '//linkedin.com', '', 'linkedin.com']) {
    assert.equal(matches(value, 'linkedin.com'), false, value);
  }
});
