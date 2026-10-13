const { test, expect } = require('@playwright/test');

const attack = '\"><img src=x onerror="window.__resumeXss=1">&\' résumé';
const cssAttack = '0; background-image: url(https://resume-attack.invalid/leak)';

function analysisFixture(text = attack, score = cssAttack) {
  return { analysis: {
    overall_score: 82, semantic_fit: 80, semantic_fit_score: 80,
    callback_probability: { current: text, industry_average: text },
    section_scores: { experience: score, [text]: 75 },
    rewrites: [{ original: text, rewritten: text, explanation: text, impact: text, impact_score_increase: text }],
    missing_keywords: [text], found_keywords: ['Docker & Kubernetes'],
    strengths: [text], improvements: [text],
    recruiter_scan: { visible_info: { [text]: [text] }, time_to_key_info: text,
      hidden_info: [text], scanability_score: text, first_impression: text, red_flags_visible: [text] },
    ats_compatibility: { overall_score: score, parse_confidence: text,
      system_specific_scores: { [text]: score }, system_tips: { [text]: [text] }, format_issues: [text] },
    benchmark: { percentile_rank: text, compared_to_role: text, bell_curve_data: { user: score, p90: 90 },
      section_percentiles: { [text]: score }, gaps_vs_top_10_percent: [text],
      projected_success_rate: { estimated_callbacks: text, current_tier: text } },
    content_quality: { action_verbs_used: [text], repetitive_phrases: [{ phrase: text, count: text }],
      quantification_score: score, reading_level_score: score, reading_level: text,
      action_verb_diversity: score, word_count: 800, ideal_word_count_range: [text],
      power_words_count: text, passive_voice_count: text },
    interview_prep: [{ question_type: text, confidence_level: text, question: text, why_asked: text,
      preparation_tips: [text], star_answer_framework: { situation: text }, common_mistakes: [text] }],
    badges: [{ unlocked: true, rarity: text, icon: text, name: text, criteria: text, points: score }],
    active_quests: [{ status: text, progress_current: score, progress_total: 100,
      title: text, description: text, reward: text, estimated_time: text, difficulty: text,
      suggested_edits: [{ original: text, improved: text }] }],
    estimated_improvement_time: text,
  } };
}

for (const version of ['', '-v2']) {
  const path = `/resume-review${version}`;
  test(`${path}: upload treats a filename as text and Remove works with Enter`, async ({ page }) => {
    await page.goto(path);
    await page.keyboard.press('Tab');
    await expect(page.getByRole('link', { name: 'Skip to résumé workspace' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('#resumeMain')).toBeFocused();
    const filename = '<img src=x onerror=window.__resumeXss=1>.txt';
    await page.getByRole('button', { name: 'Upload résumé file' }).focus();
    const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.keyboard.press('Space')]);
    await chooser.setFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from('Synthetic resume') });
    await expect(page.locator('.file-info-name')).toHaveText(`📄 ${filename}`);
    await expect(page.locator('#fileInfo img')).toHaveCount(0);
    const remove = page.getByRole('button', { name: 'Remove', exact: true });
    await remove.focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#fileInfo')).toBeHidden();
    await expect(page.locator('#resumeFile')).toHaveValue('');
    expect(await page.evaluate(() => window.__resumeXss)).toBeUndefined();
  });

  for (const malicious of [false, true]) {
    test(`${path}: ${malicious ? 'untrusted' : 'normal'} analysis preserves text and result controls`, async ({ page }) => {
      const errors = [];
      const outbound = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/resume-attack.invalid/**', route => { outbound.push(route.request().url()); return route.abort(); });
      const data = malicious ? analysisFixture() : analysisFixture('Built Docker & Kubernetes services', 82);
      await page.route('**/resume/analyze**', route => route.fulfill({ json: data }));
      await page.goto(path);
      await page.locator('#resumeInput').fill('Synthetic technical resume for the rendering regression');
      await page.locator('#analyzeBtn').click();
      await expect(page.locator('#resultsContent')).toBeVisible();
      await expect(page.locator('#analyzeBtn')).toBeEnabled();
      await expect(page.locator('#loadingState')).toBeHidden();
      await expect(page.locator('#strengthsList')).toContainText(data.analysis.strengths[0]);
      await expect(page.locator('#rewritesList')).toContainText(data.analysis.rewrites[0].original);
      await expect(page.locator('#keywordHeatmap')).toContainText('Docker & Kubernetes');
      await expect(page.locator('#resultsContent img, #resultsContent script, #resultsContent iframe')).toHaveCount(0);
      expect(await page.evaluate(() => window.__resumeXss)).toBeUndefined();
      if (version) {
        const width = await page.locator('.system-fill').first().evaluate(element => element.style.width);
        expect(width).toBe(malicious ? '0%' : '82%');
        expect(await page.locator('#resultsContent [onerror], #resultsContent [onload]').count()).toBe(0);
      }
      expect(outbound).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
}
