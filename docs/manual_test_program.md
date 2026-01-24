# SFO Manual Test Program (v0.7)

## How to use
- Status values: TODO, PASS, FAIL, SKIP.
- When you report results, send updates like "PASS AUTH-002" or "FAIL CAP-G-004 - weekly cap not enforced" and I will mark the file.

## Preconditions (optional)
- Seed data for repeatable testing: `python3 scripts/seed_test_data.py --reset`.
- Start the app: `uvicorn main:app --reload`.
- Auth tests require `SFO_PASSWORD` (and optionally `SFO_USERNAME`).
- Cozi calendar tests require `COZI_ICS_URL`.

## Authentication and session (AUTH)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| AUTH-001 | Login required when auth enabled | Set `SFO_PASSWORD`; open `/` in a fresh browser session | Redirects to `/login` | SKIP |
| AUTH-002 | Login succeeds with valid credentials | Enter correct username/password and submit | Redirects to `/` and session stays logged in | SKIP |
| AUTH-003 | Login fails with invalid credentials | Submit invalid password | Error message shown on login form | SKIP |
| AUTH-004 | Logout ends session | Click Log out in header | Redirects to `/login` and pages require login again | SKIP |

## Navigation and global UI (NAV)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| NAV-001 | Header links work | Click Long Term, Health, Tasks, Export | Each link loads the expected page | PASS |
| NAV-002 | Profile link works | Click Me in header | `/profile` loads | PASS |
| NAV-003 | Charlie widget toggles | Open and close the coach panel | Panel opens/closes without layout break | PASS |
| NAV-004 | Quick capture modal toggles | Click Quick on Home; close with X | Modal opens and closes cleanly | PASS |

## Onboarding and profile (ONB/PRF)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| ONB-001 | Onboarding page loads | Open `/onboarding` | Form loads without errors | PASS |
| ONB-002 | Onboarding saves profile | Fill name/why/values and submit | Redirects to `/` with welcome success | PASS |
| ONB-003 | Onboarding seeds projects | Enter work/personal project lists and submit | Projects created; weekly focus caps applied (4 work, 3 personal) | PASS |
| PRF-001 | Profile update persists | Update profile fields and save | Redirects with success and fields persist | PASS |
| PRF-002 | Profile Why cue appears | Set Why in profile; return Home | Why cue shows in Now panel | PASS |

## Home, inbox, and calendar (HOME)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| HOME-001 | Home loads core panels | Open `/` | Inbox, Today tasks, Now, calendar render without errors | PASS |
| HOME-002 | Quick capture saves to inbox | Open Quick modal; enter title; save | Task appears in Inbox list | PASS |
| HOME-003 | Guided capture modal opens | Click Guided from Home | Guided modal opens and closes cleanly | PASS |
| HOME-004 | Process inbox item | Click Process on an inbox item; complete guided flow | Item removed from Inbox; task/project created | PASS |
| HOME-005 | Edit block title from calendar | Click Edit on a block; change title; save | Title updates on calendar and blocks list | TODO |
| HOME-006 | Week calendar view | Click Week from Home | `/calendar/week` loads and shows week grid | TODO |
| HOME-007 | Cozi events (conditional) | Set `COZI_ICS_URL`; load Home | External events appear and Cozi status OK | TODO |

## Capture - quick (CAP-Q)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| CAP-Q-001 | Missing title error | Submit capture form with empty title | Redirects with "Title is required" | TODO |
| CAP-Q-002 | Decide later -> inbox | Capture with kind Decide later | Task created in Inbox (Later bucket) | TODO |
| CAP-Q-003 | Task capture requires displacement | Select Task; submit without confirmation | Redirects with displacement error | TODO |
| CAP-Q-004 | Task capture creates task | Select Task; confirm displacement; save | Task appears in Tasks/Today as chosen | TODO |
| CAP-Q-005 | Project capture enforces weekly cap | Create 5th active work project | Error shows weekly cap reached | TODO |
| CAP-Q-006 | Project capture creates project | Create project with color/time horizon | Project appears with color and horizon | TODO |
| CAP-Q-007 | Time block capture validates fields | Submit without date/time or block type | Error shown; block not created | TODO |
| CAP-Q-008 | Time block capture creates block | Fill date/time/duration/type; save | Block appears on Home calendar and Blocks page | TODO |
| CAP-Q-009 | "Don't know" opens guided | Select "Don't know" and submit | Guided modal opens with prefill | TODO |

## Capture - guided (CAP-G)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| CAP-G-001 | Step 1 requires name | Try Next without capture text | Next blocked; inline error shown | TODO |
| CAP-G-002 | OPP creates waiting item | Choose OPP; save | Waiting On item created for the task | TODO |
| CAP-G-003 | Task path saves details | Choose Task; set project, block type, duration | Task saved with details | TODO |
| CAP-G-004 | Project path respects cap | Choose Project; include this week beyond cap | Error shown; project not created | TODO |
| CAP-G-005 | Displacement check required | Save without displacement check | Redirect with displacement error | TODO |
| CAP-G-006 | Process inbox source task | Start from Process; save as task | Inbox task updated and removed from Inbox | TODO |
| CAP-G-007 | Process inbox -> project | Start from Process; save as project | Inbox task archived; project created | TODO |
| CAP-G-008 | Not sure flow clarifies | Select Not sure; answer prompts; choose task/project | Extra steps show and route to correct flow | PASS |

## Tasks board (TASK)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| TASK-001 | Active (By time) loads | Open `/tasks/time` | Time buckets render with tasks | PASS |
| TASK-002 | Active (By project) loads | Open `/tasks/project` | Project columns render with tasks | TODO |
| TASK-003 | Completed page loads | Open `/tasks/completed` | Completed panels render | TODO |
| TASK-004 | Archived page loads | Open `/tasks/archived` | Archived list renders | TODO |
| TASK-005 | Edit task details | Edit a task; change project/when/block/duration | Changes persist and display | TODO |
| TASK-006 | Mark task done | Click Done on a task | Moves to Completed page | TODO |
| TASK-007 | Reopen task | Reopen from Completed page | Returns to Active page | TODO |
| TASK-008 | Archive task | Archive a task | Task moves to Archived page | TODO |
| TASK-009 | Bulk archive completed | Select multiple completed; archive | Selected tasks move to Archived page | TODO |
| TASK-010 | Completed this week | Complete a task today | Appears under Completed this week | TODO |

## Blocks (BLOCK)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| BLOCK-001 | Blocks page loads | Open `/blocks` | Blocks list and schedule-ready tasks render | TODO |
| BLOCK-002 | Schedule task | Schedule a ready task with date/time/type | Block created; task scheduled_for set | TODO |
| BLOCK-003 | Create appointment | Add appointment block | Appointment appears in list and calendar | TODO |
| BLOCK-004 | Update block title | Edit a block title on Blocks page | Title updates and persists | TODO |
| BLOCK-005 | Unschedule block | Unschedule a block tied to a task | Block removed; task unscheduled | TODO |
| BLOCK-006 | Block cannot span midnight | Create block spanning midnight | Error shown; block not created | TODO |

## Weekly review (WEEK)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| WEEK-001 | Weekly review page | Open `/weekly` | Weekly counts and project list render | TODO |
| WEEK-002 | Weekly wizard | Open `/weekly/wizard` | Due resurface + completed list shown | TODO |
| WEEK-003 | Toggle weekly focus | Toggle a project on/off | Weekly counts update; cap enforced | TODO |
| WEEK-004 | Complete weekly review | Submit weekly review form | Success message appears | TODO |

## Resurface (RES)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| RES-001 | Resurface page | Open `/resurface` | Shows due tasks only (not done/archived) | TODO |
| RES-002 | Pull into week | Click Move to week on a task | Task bucket set to Week and resurface cleared | TODO |

## Waiting on (WAIT)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| WAIT-001 | Waiting list loads | Open `/waiting` | Waiting items render | TODO |
| WAIT-002 | Save follow-up | Set follow-up date | Date persists and success shows | TODO |
| WAIT-003 | Resolve waiting item | Click Resolve | Item removed from list | TODO |

## Rituals (RIT)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| RIT-001 | Morning ritual loads | Open `/ritual/morning` | Form and last entry render | TODO |
| RIT-002 | Save morning ritual | Fill fields; Save | Redirect with success; entry persisted | TODO |
| RIT-003 | Save midday ritual | Open `/ritual/midday`; Save | Redirect with success | TODO |
| RIT-004 | Save evening ritual | Open `/ritual/evening`; Save | Redirect with success | TODO |
| RIT-005 | Ritual status on Home | Complete a ritual; return Home | Ritual button shows done state | TODO |

## Long term planning (LT)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| LT-001 | Horizon map loads | Open `/long-term` | Columns render with counts | TODO |
| LT-002 | Drag project horizon | Drag a project to another column | Horizon updates; weekly focus toggles if Week | TODO |
| LT-003 | Edit project details | Edit title/category/horizon/target/why | Changes persist | TODO |
| LT-004 | Project pyramid view | Open `/long-term/pyramid` | Pyramid view renders | TODO |
| LT-005 | Roadmaps view | Open `/long-term/roadmaps` | Roadmaps view renders | TODO |
| LT-006 | Weekly cap on horizon move | Move project to Week beyond cap | Error or refusal; cap enforced | TODO |

## Health (HLTH)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| HLTH-001 | Health dashboard loads | Open `/health` | Key metrics, charts, goals render | TODO |
| HLTH-002 | Add metric entry | Enter valid number; save | Entry shows in recent list and chart | TODO |
| HLTH-003 | Invalid entry rejected | Enter non-numeric value | Error shown; entry not created | TODO |
| HLTH-004 | Add health goal | Create goal with title | Goal appears in list | TODO |
| HLTH-005 | Add blood pressure | Submit systolic + diastolic | Entries created for both metrics | TODO |
| HLTH-006 | Add custom metric | Create custom metric; add entry | Metric appears and accepts entries | TODO |
| HLTH-007 | Category pages render | Open diet/weight/fitness/strength/flexibility | Charts and recent entries render | TODO |

## Export (EXP)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| EXP-001 | Export page loads | Open `/export` | Options render and defaults set | TODO |
| EXP-002 | Export default ZIP | Download export with defaults | ZIP contains JSON + CSV + summary | TODO |
| EXP-003 | Export with filters | Select range (week/month/quarter/year) | Export includes only data in range | TODO |
| EXP-004 | Export include/exclude sets | Toggle datasets (blocks, rituals, coach) | ZIP includes only selected sets | TODO |

## Coach and nudges (COACH/NUDGE)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| COACH-001 | Coach panel basics | Open panel; send message; close | Reply appears; panel closes | TODO |
| COACH-002 | Help me with this screen | Click "Help me with what I am looking at" | Coach responds with screen-aware guidance | TODO |
| COACH-003 | Clear chat | Click Clear chat | Chat history cleared | TODO |
| COACH-004 | Capture via chat | Send "Capture inbox Buy milk" | Inbox task created | TODO |
| COACH-005 | Add task via chat | Send "Add task today Draft outline" | Task created in Today | TODO |
| COACH-006 | Set One Thing via chat | Send "Set my one thing to X" | Home shows One Thing | TODO |
| COACH-007 | Schedule block via chat | Send "Schedule block 2pm to 3pm for X" | Block created on today | TODO |
| NUDGE-001 | Nudge appears when due | Create due condition; refresh | Nudge shows with link | TODO |
| NUDGE-002 | Nudge link works | Click nudge link | Navigates to target page | TODO |

## API (optional manual checks) (API)
| ID | Scenario | Steps | Expected | Status |
| --- | --- | --- | --- | --- |
| API-001 | Unauthorized API blocked | Call `/api/tasks` without token | 401 response | TODO |
| API-002 | Tasks CRUD | Create, update, delete task | API returns expected data and status | TODO |
| API-003 | Projects CRUD + cap | Create 5th active work project | 400 weekly cap error | TODO |
