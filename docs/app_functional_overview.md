# Start Finishing Organiser (SFO) — Functional Overview (v0.732)

This document explains how SFO works from a user and product perspective: screens, cards,
information types, and the flow of work through the system.

---

## What this app is
SFO is a single-user organiser built around *Start Finishing* principles. It helps you:
- Capture everything fast (so nothing gets lost).
- Decide what actually matters this week (4+3 cap).
- Protect time with Focus/Admin/Social/Recovery blocks.
- Keep a daily “One Thing” and “Frog” visible.
- Review weekly and resurface parked work.
- Track health and export your data.

The UI uses “pills” and “cards” to keep work readable: each pill is a status or tag; each card is a
work unit (task, project, block, metric, etc).

---

## Current strategy update (inbox and later handling)

The active, approved design direction for inbox processing and "later" containment is documented in:

- `docs/inbox_intent_container_strategy.md`

Key behavior direction:

- Process-time intent classification (support project, learn/explore, enjoy/recover, park/let go).
- Inbox actions prioritize explicit routing over default task creation.
- Learning is bounded through curated picks, not unlimited visible backlog.
- Enjoy/recover remains separate from work execution views.

This strategy is being rolled out in phases, with scorecard metrics used to tune guardrail strictness.

---

## Core concepts (how the system thinks)
- **Inbox**: A temporary parking place. Items can live in the Inbox *and* on the Tasks board.
  Inbox = “needs sorting/deciding,” not “not real.”
- **4+3 weekly focus**: You pick up to 4 work projects and 3 personal projects as your weekly focus.
  This is enforced across weekly review and project planning.
- **Time horizons**: Today -> Week -> Month -> Quarter -> Later. Tasks and projects move between these
  horizons as you plan.
- **Resurfacing**: Items parked in Month/Quarter/Later return to review when due.
- **Blocks**: Focus/Admin/Social/Recovery time blocks are the primary way you reserve attention.
- **One Thing + Frog**: A daily highlight (One Thing) and the dread-heavy task (Frog) are surfaced on Home.

---

## What the app stores (user-level data types)

### Projects
Projects are larger commitments with horizon, category, and success cues.
Common info:
- Title, description, category (Work/Personal), horizon (Week/Month/Quarter/Year/Later).
- Optional target date, size, success level, and color.
- **Why** text to anchor meaning.
- **Success Pack**: guides, peers, supporters, beneficiaries.
- Weekly focus flag (counts toward 4+3).

### Tasks
Tasks are single-sitting items that sit inside a horizon.
Common info:
- Title + description.
- Inbox flag (in inbox or not).
- When bucket (Today/Week/Month/Quarter/Later).
- Block type (Focus/Admin/Social/Recovery).
- Duration, Frog flag, alignment tag.
- Status: Pending, In Progress, Done, Archived/Cancelled.
- Resurface date (for Month/Quarter/Later).
- Optional project association.

### Blocks (time on the calendar)
Blocks represent time you reserve:
- Date, start/end time, block type.
- Optional title and notes.
- Can attach to a project or task.

### Ritual entries (morning / midday / evening)
Structured daily check-ins. Each ritual stores:
- Morning: grounding, plan review, One Thing, Frog, block plan, gratitude, etc.
- Midday: alignment check, surprises, adjustments, AAR notes.
- Evening: wins, adjustments, shutdown, breadcrumbs, reflection.

### Health tracking
Health metrics, entries, and goals:
- Custom metrics with category + unit.
- Entries with value/date/notes.
- Goals with target value/date.
- Blood pressure logs capture systolic + diastolic together.

### Waiting On / OPP
Items where someone else owns the priority:
- Description + person.
- Follow-up date and resolve action.

### Coach + Guidance
- Charlie coach chat history.
- Nudges / guidance reminders based on patterns or thresholds.

### Email imports (optional)
Gmail messages can be imported as inbox items (with subject + snippet), then processed like any task.

---

## Global UI elements

### Header
Persistent navigation: Home, Long Term, Tasks, Health, Export.
Shows:
- App name + version pill.
- “Now” strip (current focus text).
- Clock and date.
- Optional login/logout.
- Charlie coach button.
- Profile shortcut.

### Quick Capture (modal)
Always available. A single input saves directly to Inbox for later processing.

### Charlie coach panel
A conversational helper that can:
- Explain the current screen (“Help me with what I’m looking at”).
- Capture a task or inbox item by text.
- Schedule time blocks by natural language.
- Set “One Thing” via chat.
- Show nudges and quick actions.

---

## Screens (what each one does)

### Home / Today
This is the daily execution dashboard.

**Panels**
- **Inbox**: List of inbox tasks. Header actions: `Quick`, `Process`, and `Lists` (Containers, Waiting, Recycle bin).
  Each item shows title + when bucket + project pill, with hover actions:
  - `P` Process (opens guided capture prefilled).
  - `L` route to Learning.
  - `E` route to Enjoy.
  - `K` route to Park.
  - `🗑` move to recycle bin.
- **Today calendar**: Day schedule with:
  - Internal blocks (Focus/Admin/Social/Recovery).
  - External calendar events (Cozi).
  - “Now” line indicator.
  - Inline edit for block titles.
- **Now**: Current block (if active), One Thing/Frog, and ritual shortcuts.
- **Today tasks**: Tasks in Today bucket with block type / frog / alignment pills.

**Modal**
- **Inbox detail**: Edit description for an inbox item, then Save, Process, route to Learning/Enjoy/Park, or move to recycle bin.

---

### Inbox containers
Dedicated lists page for non-work intake containers:
- **Learning**, **Enjoy**, **Parked**, and **Recycle bin** tabs.
- Restore actions for items that should return to active planning.
- Recycle bin supports:
  - **Empty Recycle Bin** (destructive, confirmed).
  - **Clean Expired** (explicit cleanup using retention policy).

---

### Capture (full page)
Catch-all capture form that can create:
1) **Decide later** -> Inbox item.
2) **Task** -> with project, horizon, block type, duration, frog.
3) **Project** -> with category, horizon, color, weekly focus decision, and Why.
4) **Time block** -> direct scheduling.
5) **Don’t know** -> opens guided capture.

---

### Guided Capture (wizard modal)
Step-by-step capture for clarity and decision-making.

**Step 1: Define the item**
- Capture text + details.
- Owner type: Mine / Shared / OPP.
- If OPP: optional “waiting on” person (creates a Waiting On entry).

**Step 2: Decide task vs project vs decide later**
- Task, Project, Decide Later (Inbox), or Not Sure.
- If Not Sure: quick clarity questions and a suggestion.

**Step 3: Horizon**
- Today/Week/Month/Quarter/Later.
- For projects: horizon + weekly focus toggle.

**Step 4: Block type + duration**
- Optional block type, duration, frog.
- Block type now includes inline guidance and auto-suggestion from capture text.

**Special flow: “Process inbox item”**
Guided capture can be launched from an inbox item. In source-item mode, intent choice is explicit:
- Support a Project (task/project conversion flow)
- Learn / Explore
- Enjoy / Recover
- Park / Let Go
Non-support intents route the item to its container without creating a schedulable task.

---

### Tasks
The task board is the execution hub. Tasks can be viewed two ways:

**Active (By time)**
- Columns: Today / Week / Month / Quarter / Later.
- Drag-and-drop between columns updates the horizon.

**Active (By project)**
- Columns by project (plus “No project”).
- Drag-and-drop between projects updates task ownership.

**Task cards**
Show title, description, and pills for:
- When bucket, block type, frog, alignment, project.

**Inline actions**
- Complete task (✓).
- Archive task (🗑).

**Task edit modal**
Click a task to edit title/description, project, when, block type, duration, alignment, frog.
If the task is not already in the Inbox, a **“Send to Inbox”** button appears.

**Completed**
- “Completed this week” checklist with bulk archive.
- Full completed list with Reopen or Archive actions.
- Server-side pagination for longer histories.

**Archived**
- Archived list with Restore.
- If task was archived from Inbox, restore returns it to Inbox.
- Server-side pagination for longer histories.

---

### Blocks (planner)
Schedule work and appointments.

**Blocks list**
- Shows block title, date, time, type.
- Inline title edit.
- Unschedule action.

**Tasks to schedule**
- Tasks that already have block type + duration.
- Schedule them onto the calendar directly.

---

### Week calendar
7-day grid view with:
- Internal blocks.
- External calendar events.
- Inline block title editing.

---

### Weekly review
Two ways to review:

**Weekly focus page**
- Shows current 4+3 projects.
- Shows items due to resurface.
- Offers “Pull into this week.”

**Weekly wizard (step-by-step)**
1) Wins + movement (completed tasks).
2) Choose weekly focus (toggle 4+3).
3) Resurface due items.
4) Plan focus blocks.
5) Archive completed + reflect (wins/adjustments).

---

### Resurface
Dedicated page for tasks parked in Month/Quarter/Later that are due now.
Each task can be “pulled into this week.”

---

### Long-term planning
Three linked views:

**Horizon map**
- Columns by horizon with draggable project cards.
- Inline project editing.

**Project pyramid**
- Year -> Quarter -> Month -> Week tiers.
- Projects move between tiers via drag.

**Project roadmaps**
- Roadmap cards for year/quarter projects.
- Surface Why, success level, drag points, success pack.
- Edit projects in-place.

---

### Waiting On / OPP
List of items captured as “Other People’s Priority.”
For each item you can:
- Set a follow-up date.
- Resolve when done.

---

### Rituals (morning / midday / evening)
Daily check-ins that create ritual entries.

**Morning**
- Grounding, plan review, focus time reality check.
- Why cue, gratitude, One Thing, Frog.
- Focus/Admin block planning.
- Email boundary plan.
- Emotional intent + energy tag.

**Midday**
- Alignment check + surprises.
- Adjustments + updated One Thing/Frog.
- Quick AAR (after-action review).

**Evening**
- Wins, adjustments, shutdown steps, breadcrumbs.
- Reflection notes.

Home uses ritual status to show what’s next.

---

### Health
Health is a full module with:

**Dashboard + trackers hub**
- Dashboard: key metrics, quick log, goals, blood pressure quick log, custom metrics, trend board.
- Trackers hub: category entry point for all health tracking surfaces.

**Category pages**
- Diet, Weight, Fitness, Strength, Flexibility.
- Each category has: log form, trend charts, recent entries.

**Supplements**
- Dedicated supplements page to log what you are taking, dosage/context notes, and timing.

**Exercise plan**
- Weekly training schedule across fitness/strength/flexibility focuses.
- Session planning and links into related health categories.

**Training live**
- Day-of execution page for logging sets/reps/duration.
- Includes quick counter and rest timer tools.
- Shows today schedule, recent logs, weekly snapshot, and overall training plan editor.

---

### Export
Export produces a ZIP containing JSON + CSV.
Options:
- Time window (all, year, quarter, month, week).
- Data sets to include (profile, projects, tasks, health, blocks, rituals, waiting, coach, guidance).
- Includes backup manifest + checksums and restore notes.
- Default export includes a full SQLite snapshot (`database.sqlite3`) for backup-grade recovery when enabled.
- `/export/health` reports backup readiness and schema migration state.

---

### Profile
User profile for:
- Name, Why, values.
- Energy profile and workday bounds.
- Weekly review day.
- Focus block preference.

---

### Onboarding
Step-by-step setup that:
- Captures name + Why.
- Captures values + energy + workday preferences.
- Seeds weekly focus projects (work + personal).

---

### Login (optional)
If auth is enabled, users log in with password (and optionally username).

---

### API (optional, token/session protected)
- `/api/projects` and `/api/tasks` list endpoints are paginated.
- List responses return envelope metadata:
  - `items`, `page`, `page_size`, `total`, `total_pages`.
- Create/update/delete endpoints remain available for projects and tasks.

---

## Information flow (how work moves through the system)

1) **Capture**
   - Quick capture or full capture.
   - If unclear, send to Inbox.

2) **Process**
   - Inbox item gets “processed” via guided capture into Task or Project.
   - Items can be sent back to Inbox if they need re-clarifying.

3) **Plan**
   - Assign task horizon (Today/Week/etc).
   - Attach to projects.
   - Assign block type + duration.
   - Choose weekly focus projects (4+3).

4) **Schedule**
   - Convert task + duration into time blocks.
   - Blocks show on Today and Week calendar.

5) **Execute**
   - Home shows current block, One Thing, Frog, and Today tasks.
   - Tasks can be completed, archived, or returned to Inbox.

6) **Review**
   - Weekly review wizard guides wins -> focus -> resurface -> archive.
   - Resurface brings parked tasks back into the active horizon.

7) **Track**
   - Rituals record daily check-ins.
   - Health entries track metrics and goals.

8) **Export**
   - Export data for backup or analysis.

---

## Integrations (user-visible behavior)
- **Gmail (optional)**: Emails can be imported as Inbox items, then processed like tasks.
- **Cozi calendar (optional)**: External events appear in Today and Week calendars.
- **Desktop app**: Same UI, with local data storage and optional bundled Gmail credentials.

---

## Glossary of common UI elements
- **Pill**: Small label showing category, status, or counts.
- **Card**: Larger item container (task, project, block, metric, roadmap).
- **Now**: The current focus strip and active block on Home.
- **One Thing**: The highest-value task for the day.
- **Frog**: The dread-heavy task you want to tackle early.
