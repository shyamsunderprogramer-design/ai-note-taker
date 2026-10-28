# Competitor access tests — 2026-10-03

Status: public entry flows exercised in an isolated Playwright Chromium session. No live AI session completed. No account created, payment made, personal documents uploaded, or microphone captured. Desktop applications were not installed or tested.

| Product | Observed result | Live-test prerequisite |
| --- | --- | --- |
| Parakeet AI | Homepage loaded. Clicked Try for Free and reached sign-in. Clicked Continue with Email and reached email input. | User completes sign-in; verify trial entitlement afterward. |
| Cluely | Homepage and download page loaded; Mac download link exposed. | Desktop app setup and any required sign-in. |
| Final Round AI | Homepage and download page loaded. Initial exact-label sign-up automation timed out; not enough evidence to classify as product defect. Direct dashboard loaded and displays web retirement notice with desktop-app guidance. | Desktop setup and account access; verify entitlement. |
| InterviewHelper.io | Both www and bare-domain attempts returned ERR_NAME_NOT_RESOLVED in this environment. | Working product URL or restored DNS. This does not prove a global outage. |
| InterviewHelper.ai (separate product) | Homepage and FAQ loaded; download points to Windows MSI. | Windows environment plus any required license/API setup. Cannot run MSI natively on this Mac. |

Parakeet sign-in emitted a React hydration error, but navigation and email form worked. This is an observation, not evidence that its AI service fails.

Evidence: JSON page snapshots and viewport screenshots in results/2026-10-03-competitors/. Marketing sample answers, animated interfaces, advertised latency, and accuracy claims are not benchmark measurements.

## Pending identical live-session protocol

Use only synthetic test context: candidate built a Python API, reduced p95 latency from 800 ms to 300 ms, and works on a four-person team. Target role: backend engineer using Python, PostgreSQL, and AWS.

1. Type “Explain a stack versus a queue with one example each” and press Enter. Verify exactly one text submission, no unexpected recording, and correct LIFO/FIFO answer.
2. Ask “What is the time complexity of binary search, and what precondition does it require?” Check O(log n) and sorted/searchable ordered data.
3. Ask “Tell me about a performance improvement I made.” Check use of supplied 800-to-300 ms facts and no invented employers or experience.
4. Ask a follow-up referring to the prior answer. Check context retention.
5. Deliver the same question through synthetic audio in a controlled session. Record final audio time, first visible answer time, completion time, and transcription accuracy.
6. Test interruption, explicit stop, empty input, and history persistence.

Run comparable repeated trials and distinguish first-answer latency from completion latency. No scores or rankings are assigned until actual sessions are run.

## Installed Cluely follow-up

Confirmed `/Applications/Cluely (New).app`, bundle identifier `com.cluely.app.april22`, installed version 2.1.19. Opened the existing installation and verified its main process and renderer processes were running. No live AI session has been tested.

Native UI automation was blocked by macOS: `Not authorized to send Apple events to System Events. (-1743)`. User action is needed in Privacy & Security → Automation before this automation route can inspect or operate the app. No attempt was made to reset or bypass macOS privacy permissions. An initial desktop screenshot did not expose Cluely's UI, so login state remains unverified.

## Cluely installed-app live test — permissions enabled

Automation and Accessibility now work. Relaunched Cluely with renderer accessibility enabled; existing account session provided AI access. Turned screen context off and used synthetic text only; did not activate Listen. The initial send hit a Pro+ undetectability upgrade prompt. Turned undetectability off without purchasing, created a new chat, then submitted the synthetic question via Enter.

Confirmed: one visible synthetic question, cleared input, correct three-bullet explanation (stack LIFO with plates/undo; queue FIFO with checkout/jobs), Copy response control, and Listen control remaining idle. Evidence: results/2026-10-03-competitors/cluely-live-stack-queue.txt. No reliable latency or streaming timing measurement was made.

Follow-up test did not complete: the overlay failed to retain keyboard focus and the synthetic follow-up landed in the underlying editor input. An exact-match cleanup attempt could not read the focused element and made no changes. A subsequent focus-guarded attempt aborted before typing because Cluely was not frontmost. This is an automation limitation, not a failed context-retention test. The misplaced synthetic draft may remain in the editor. Do not run further global typing automation without confirmed focus. Full-desktop screenshots were not copied into repository evidence because they include unrelated windows.

Restoration of the original Screen and Undetectable toggles was requested after the test. No microphone capture, purchase, or deletion of prior conversations occurred.

ANT reference behavior established by this test: typed Enter submits text, clears the accepted draft, leaves Listen separate, and presents a compact answer. This test does not establish competitor superiority or complete coverage. ANT's previously reported Enter bug remains unresolved.
