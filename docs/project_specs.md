---
app_name: "Meaningful Work Organiser"
version: "0.1-prototype"
author: "Richard Davies"
created_for: "Personal use, extensible to others later"
primary_reference: "Start Finishing – Charlie Gilkey"
philosophy:
  core_principles:
    - "Everything that matters is a project."
    - "We thrive by doing our best work."
    - "Best work requires focus blocks and realistic capacity planning."
    - "The Five Projects Rule prevents overload."
    - "Displacement is real: every yes displaces countless other yeses."
    - "Intention + Awareness + Boundaries + Courage + Discipline are the keys."
    - "Head trash, drag points, and thrashing are normal; we design for them."
    - "Success Packs and aligned teams make finishing possible."
    - "No date = no finish."
    - "Plans create clarity, not certainty."
  user_values:
    - "Meaning over busyness."
    - "Presence over reactivity."
    - "Connection over control."
    - "Sustainable progress over heroic pushes."
  app_role: "Steady, wise co-pilot that helps Richard live Start Finishing, not just read it."

tone:
  primary: "Purposeful + Focused"
  secondary:
    - "Calm + Clear"
    - "Quietly Wise"
  human_undertone:
    style: "Warm but not cheesy, Kiwi-understated"
    rules:
      - "No toxic positivity."
      - "No shaming language."
      - "Use curiosity and invitations, not commands."

platforms:
  version_1:
    - "Browser-based web app (desktop-first, mobile-friendly)."
  future:
    - "MacOS wrapper (e.g. Tauri/Electron)."
    - "iOS client (native or PWA)."

tech_stack:
  backend:
    language: "Python"
    suggested_frameworks: ["FastAPI", "Flask"]
  frontend:
    options:
      - "Simple HTML/CSS/JS (modular, progressively upgradable)."
      - "React-lite (if component-based UI is preferred)."
  storage:
    prototype: "Local JSON/YAML files or SQLite."
    future: "PostgreSQL or equivalent."
  ai_integration:
    codex_role: "Generate boilerplate, scaffolding, and refactors from this spec."
    future_llm_role:
      - "Email triage and classification."
      - "Why-alignment suggestions."
      - "Tone-aware reply drafting."

project_scope:
  version_1_goal: "Strong prototype: daily-usable for Richard’s planning and reflection, partial Trello replacement."
  trello_strategy:
    - "Continue using Trello in parallel at first."
    - "Gradually migrate core projects into this app."
    - "Long-term goal: this app becomes primary organiser."

planning_rhythms:
  supported_in_v1:
    - "Daily: Morning Check-In (10) and Evening Check-Out (15)."
    - "Weekly: High-level Week review & planning."
  planned_for_v2_plus:
    - "Monthly planning."
    - "Quarterly review & AAR."
    - "Project-level AAR templates."

constraints_and_rules:
  five_projects_rule:
    weekly:
      work_projects_max: 4
      personal_projects_max: 3
      total_projects_max: 7
    enforcement_style: "Collaborative negotiation, not hard block."
  time_blocks:
    focus_block_minutes_min: 90
    focus_block_minutes_max: 120
    admin_block_minutes_min: 30
    admin_block_minutes_max: 60
  design_constraints:
    - "System should never encourage more projects than capacity allows."
    - "Always ask: Is this actually important to you?"
    - "Always honour displacement: adding work must move or drop something."

---

# Meaningful Work Organiser — Massive Blueprint (v0.1)

## Table of Contents

1. [Philosophy Layer](#1-philosophy-layer)
2. [Cognitive Architecture](#2-cognitive-architecture)
3. [Behaviour Engines](#3-behaviour-engines)
4. [Planning Rhythms](#4-planning-rhythms)
5. [UX Principles & Tone](#5-ux-principles--tone)
6. [UX Flows](#6-ux-flows)
7. [Functional Requirements](#7-functional-requirements)
8. [Data Schema](#8-data-schema)
9. [Integration Plan](#9-integration-plan)
10. [Roadmap](#10-roadmap)
11. [Glossary & Concept Index](#11-glossary--concept-index)

---

## 1. Philosophy Layer

This app exists to help Richard *live* the ideas of **Start Finishing** in his daily life.

### 1.1 Core Ideas from Start Finishing

The app is built around these ideas:

- **Everything is a project.**  
  Anything that takes time, energy, and attention counts. Projects can be tiny (a day) or huge (years).  

- **Best work.**  
  Best work is the work that makes Richard come alive, feels like “I get to” not “I have to”, serves both him and others, and sits at the edge of capability and courage.  

- **The project world.**  
  Life is a series of overlapping projects; uncertainty is normal. The skill is choosing which projects to embrace now.  

- **Air Sandwich.**  
  There’s a gap between big-picture vision and daily reality, filled with: competing priorities, head trash, no realistic plan, too few resources, poor team alignment.  

- **Five Keys.**  
  Intention, Awareness, Boundaries, Courage, Discipline — the app should strengthen these, not bypass them.  

- **Thrashing.**  
  Emotional flailing around meaningful work; more thrashing usually means the work really matters.  

- **Displacement.**  
  Every yes displaces something else; time is the ultimate constraint.  

- **Five Projects Rule.**  
  At any scale, you rarely finish more than ~5 active projects; weekly: 3 is often better than 5.  

- **Chunking, Linking, Sequencing.**  
  Projects are made of verb–noun chunks (tasks) linked and sequenced over time.

- **Focus, Social, Admin, Recovery Blocks.**  
  Time is structured into blocks, not scattered minutes; focus blocks fuel best work.  

- **Momentum Planning.**  
  Continual process across daily/weekly/monthly/quarterly time scales.

### 1.2 App’s Philosophical Commitments

The app **must**:

- Protect Richard from **overload** by enforcing (softly) the Five Projects Rule.
- Centre **Why** before What: always reconnect tasks/projects to personal Why.
- Encourage **steady, sustainable progress**, not heroic burnouts.
- Normalise **resistance, drag, and thrashing**, and provide scaffolds to move through them.
- Honour **whole-life integration**: work + family + health + house, not siloed.

---

## 2. Cognitive Architecture

The cognitive architecture is the set of concepts the app is built around: how it “thinks” about Richard’s life.

### 2.1 Core Entities

- **Project**  
  A cluster of related work towards a meaningful outcome.  
  Attributes: size (Light/Moderate/Heavy), time horizon (Week/Month/Quarter/Year), Why alignment, drag points, success pack.

- **Task (Chunk)**  
  Verb–noun, 15–120 minutes in scope.  
  Attributes: first action, linked project, when-bucket (Today/This Week/This Month/Later), block type (Focus/Admin/Social), frog-ness (dread level).

- **Block**  
  A scheduled, protected container for work:
  - Focus
  - Social
  - Admin
  - Recovery

- **Time Horizons**  
  - Today  
  - This Week  
  - This Month  
  - This Quarter  
  - Year (high level, mostly for context)

- **Why**  
  Richard’s deep personal purpose, identity-level intentions, family presence commitments, emotional stance.

- **Success Pack**  
  Guides, peers, supporters, beneficiaries per project.

- **OPP (Other People’s Priorities)**  
  Incoming requests that may not align with Richard’s priorities.  

- **Drag Points & Head Trash**  
  Beliefs, fears, constraints, and no-win stories that create friction.

### 2.2 Mental Models the App Encodes

- **Air Sandwich Model**  
  The app sees the gap between vision and reality and helps Richard:
  - Align competing priorities.
  - Clear head trash.
  - Build realistic plans.
  - Surface resource constraints.
  - Align his team/success pack.

- **Displacement Model**  
  Whenever something is added:
  - App asks: “What will this displace?”
  - Encourages explicit dropping, not hidden overload.

- **Thrashing Model**  
  When Richard touches a project repeatedly without progress:
  - App recognises thrashing.
  - Offers reflection prompts and chunking support.

- **Levels of Success Model**  
  Small / Moderate / Epic success — app allows Richard to set desired level of success per project and scale commitments accordingly.  

- **Five Keys Model**  
  For stuckness, the app frames issues in terms of:
  - Intention (do we know what we want?)
  - Awareness (do we see the reality?)
  - Boundaries (do we have space/protection?)
  - Courage (are we willing to act?)
  - Discipline (are we following through?)

---

## 3. Behaviour Engines

This is where the app’s intelligence lives.

### 3.1 Morning Ritual Engine

**Goal:** Move Richard from sleep → presence → purpose → clear plan for Today.

**Inputs:**

- Today’s calendar events.
- This week’s active projects (max 4 work + 3 personal).
- Yesterday’s plan and outcome.
- Emotional/energy state (Richard can set simple tags, e.g. “flat”, “wired”, “sad”, “anxious”, “calm”).

**Phases:**

1. **Grounding**
   - Physical: suggest short movement (strength/flexibility).
   - Physiological: confirm supplements/water done.

2. **Why Connection**
   - Show micro-Why cue.
   - Offer optional expansion into full Why panel.

3. **Gratitude & Anticipation**
   - Prompt: “What can you look forward to today?” or “One thing you’re grateful for.”

4. **Reality Scan (Today)**
   - Show calendar.
   - Highlight potential focus blocks.
   - Ask: “Is there enough focus time today for best work?”

5. **Today’s One Thing & Frog**
   - Suggest candidates based on:
     - Weekly priorities.
     - Upcoming deadlines.
     - Why alignment.
   - Ask Richard to choose One Thing.
   - Identify one Frog (dread-heavy task) to be tackled early.

6. **Block-level Planning**
   - For each available focus block:
     - Choose 1 project chunk.
   - For admin blocks:
     - Assign admin tasks (email, Teams, etc.).

7. **Emotional Intent**
   - Simple prompt: “Who do you want to be today?”  
     (e.g. “steady father”, “curious learner”, “calm collaborator”.)

**Behaviour:**

- Variety via rotating prompts.
- Core non-negotiables always included (movement, Why, gratitude, Today focus).
- Adapt prompts to recent patterns (e.g., repeated thrashing, high OPP).

---

### 3.2 Task Intake Copilot

**Goal:** Help Richard organise tasks in a thorough, systematic, meaningful way — *together* with the app.

**Entry Points:**

- Manual text input (“capture mode”).
- Paste from email/Teams (V2+).
- Quick add from any view.

**Flow (V1 logic):**

1. Capture raw text.
2. Ask: **“Is this actually important to you?”**
   - If **No** → offer:
     - Let go.
     - Archive as “Maybe/Someday”.
   - If **Yes** → proceed.

3. Ask: **“When do you want to make space for this?”**
   - Options: Today / This Week / This Month / Later.

4. Ask: **“Is this a task, or the start of a new project?”**
   - If task: require a verb–noun rewrite if needed.
   - If project: create a project shell and schedule first chunk.

5. Classify:
   - Type: Focus / Admin / Social.
   - Frog? (optional, based on dread check or manual mark.)
   - Alignment: quick selection — Aligned / Partially / Unaligned.

6. Check Weekly Load (Five Projects Rule):
   - If adding to a new project and limits exceeded:
     - Trigger collaborative negotiation:
       > “You’re at your weekly project limit.  
       > Shall we:
       > • Replace an existing project,  
       > • Move this to Month/Later,  
       > • or downgrade to a smaller experiment?”

---

### 3.3 Why Alignment Engine

**Goal:** Ensure tasks and projects serve Richard’s deeper Why.

**Features:**

- Micro-Why cue on Today view.
- Full Why panel accessible from header.
- Per-project Why link:
  - Text field: “How does this project serve your Why?”
  - Optional tags: identity, contribution, growth, family, health, etc.

**Behaviour:**

- On new project creation:
  - Ask: “Which part of your Why does this support?”
- On unaligned tasks:
  - Supportive guidance:
    > “This doesn’t seem to connect clearly to your Why.  
    > Would you like to:
    > • reframe it,  
    > • move it to Later,  
    > • or let it go?”

- Simple alignment score per day/week:
  - % of time spent on aligned work.
  - Reflected gently in weekly review.

---

### 3.4 Daily Guidance Engine (“Steady Coach”)

**Goal:** Provide predictable, supportive check-ins through the day.

**V1 Touchpoints:**

- **Before first focus block:**
  - Confirm One Thing and the chunk assigned.
  - Tiny grounding prompt.

- **After each focus block:**
  - 30–60 second micro-AAR:
    - What went well?
    - What was hard?
    - What’s the next smallest step?

- **Midday reset:**
  - Check:
    - Still aligned with Today plan?
    - Any surprises?
    - Need to adjust One Thing or Frog?

- **Evening Check-Out (15 minutes):**
  - What did you accomplish?
  - Wins (including invisible work).
  - Reassign/reschedule unfinished tasks.
  - Emotional reflection.
  - Prepare breadcrumbs for tomorrow.

---

### 3.5 Drag Point & Resistance Engine

**Goal:** Normalise and address drag points & head trash.

**Signals:**

- Repeated postponing of the same task.
- Multiple touches on a project with no completed chunks.
- Frequent reclassification of the same work item.

**Behaviours:**

- Gentle reflection prompts:
  - “Is this a skill gap, a courage gap, or a clarity gap?”
  - “What’s the smallest viable chunk that feels doable?”
- Suggest:
  - Chunking help.
  - Lowering level of success (from Epic to Moderate/Small).
  - Adding support (Success Pack).

---

### 3.6 OPP & Boundary Engine

**Goal:** Detect and manage Other People’s Priorities.

**V1:**

- Manual tagging of tasks/emails as:
  - Mine
  - Shared
  - OPP

- Prompts:
  - “Is this truly yours to carry?”
  - “Does saying yes support your best work?”

**Future (V2+):**

- Automatic classification from email/Teams content.
- Stats: time spent on OPP vs. personal priorities.

---

### 3.7 Success Pack Engine

**Goal:** Bring people into the project in a structured way.

**Per Project:**

- Lists of:
  - Guides
  - Peers
  - Supporters
  - Beneficiaries

**Behaviours:**

- Suggest adding Success Pack members on larger projects.
- Occasional nudge:
  - “It’s been a while since you updated your Success Pack for this project.”
  - “Want to share your progress with a beneficiary for motivation?”

---

## 4. Planning Rhythms

### 4.1 Daily Rhythm (V1)

- **Morning Check-In (10 minutes)**  
  Guided by Morning Ritual Engine.

- **Evening Check-Out (15 minutes)**  
  - Wins list (tasks, boundaries upheld, emotional wins).
  - Reassignment of unfinished items.
  - Short emotional/energy note.

### 4.2 Weekly Rhythm (V1-lite)

- Weekly review checklist (simplified):

  1. Celebrate 3 wins from the week.
  2. Review which projects actually moved.
  3. Curate next week’s 4 work + 3 personal projects.
  4. Assign at least 3 focus blocks to meaningful work.
  5. Update Waiting On list.
  6. Refresh 3–5 priority projects.

### 4.3 Monthly & Quarterly (Planned for V2+)

- Monthly:
  - Choose 1–3 objectives.
  - Spread across 4 weeks.
  - Budget focus blocks.
- Quarterly:
  - After Action Review for big projects.
  - Project Pyramid updates (Year → Quarter → Month → Week).

---

## 5. UX Principles & Tone

### 5.1 UX Principles

- **Clarity over clutter.**
- **Context over control**: system guides, doesn’t dominate.
- **Meaning over metrics.**
- **Few, strong visual anchors** (Today / Week / Projects / Why).
- **Gentle animations, minimal distraction.**
- **Accessible typography, calm palette.**

### 5.2 Tone Rules

- Avoid:
  - “You should…”
  - “You failed to…”
- Prefer:
  - “Would it help to…”
  - “Do you want to…”
  - “You might consider…”

---

## 6. UX Flows

### 6.1 First-Run Experience

1. Welcome: Short explanation of app purpose (Start Finishing-based).
2. Collect:
   - Richard’s Why (even as a rough draft).
   - 3–5 current important projects.
   - Typical working hours and energy profile (morning/afternoon/evening).
3. Guide:
   - Set initial 4 work + 3 personal projects for the week.
   - Identify first three focus blocks.
4. Land on Today with a minimal plan.

### 6.2 Daily Start Flow

- Open app → Morning Ritual Engine runs:
  - Grounding → Why → Gratitude → Today reality → One Thing/Frog → Blocks → Emotional intent.
- Land on Today view with:
  - One Thing
  - Frog
  - Focus chunks
  - Calendar
  - Micro-Why cue

### 6.3 Task Capture Flow

- Tap “Capture”.
- Type or paste.
- Task Intake Copilot runs:
  - Important? → When? → Task vs Project → Classification.
- If overload, collaborative negotiation.

### 6.4 Weekly Review Flow (Lite)

- Prompted on chosen day (e.g. Saturday/Sunday):
  - Show accomplishments.
  - Show project movement.
  - Choose next week’s projects.
  - Allocate focus blocks.

---

## 7. Functional Requirements

### 7.1 Version 1 — Must Haves

1. **User Profile**
   - Store Why, energy preferences, basic settings.

2. **Project Management**
   - Create, edit, archive projects.
   - Fields: title, description, size, status, Why-link, level_of_success (Small/Moderate/Epic).

3. **Task Management**
   - Create, edit, complete tasks.
   - Verb–noun enforced as much as feasible.
   - When-bucket: Today/This Week/This Month/Later.

4. **Today View**
   - List of Today’s tasks (grouped by block type).
   - One Thing & Frog highlight.
   - Calendar events (prototype: manual entries or simple ICS feed later).
   - Micro-Why cue.

5. **Week View**
   - List of active projects (4 work + 3 personal).
   - Assigned focus blocks and chunks.

6. **Morning Ritual**
   - Minimal flow as described.
   - Configurable start time.

7. **Evening Check-Out**
   - Wins capture.
   - Reassignment of tasks.
   - Short reflection.

8. **Steady Coach Touchpoints**
   - Before first focus block.
   - After each focus block (simple micro-AAR).
   - Midday reset.
   - Context-aware Charlie coach widget available on every screen, advice-only.
   - In-app Guide for “how to use” questions.

9. **Why Alignment**
   - Per-project Why field.
   - Quick alignment set per task.

10. **Basic Waiting On / OPP**
    - Waiting On list with “Waiting on [Person] for [Action]”.
    - Manual OPP tag.

### 7.2 Version 2 — Planned Features

- Gmail + Outlook/Microsoft 365 integration.
- Calendar unification (work + family).
- Email-based Task Intake Copilot.
- Basic AI draft replies aligned with Richard’s tone.
- Monthly + Quarterly views & flows.
- Success Pack reminders.

### 7.3 Version 3+ — Future

- Native Mac and iOS apps.
- Advanced emotional state modelling.
- Deep Thrashing detection and interventions.
- Rich analytics with a meaning-first framing.

---

## 8. Data Schema

*(Expressed conceptually; actual implementation can be SQL or document-based.)*

### 8.1 User

- id
- name
- why_primary_text
- why_supporting_texts[]
- values[]
- energy_profile (e.g. "morning", "afternoon", "evening")
- settings (JSON blob)

### 8.2 Project

- id
- user_id
- title
- description
- size (Light/Moderate/Heavy)
- status (Active/Paused/Completed/Archived)
- time_horizon (Week/Month/Quarter/Year)
- start_date
- target_date
- level_of_success (Small/Moderate/Epic)
- why_link_text
- tags[]
- success_pack_id
- drag_points_notes
- created_at
- updated_at

### 8.3 Task

- id
- project_id
- user_id
- verb_noun
- description
- when_bucket (Today/Week/Month/Later)
- block_type (Focus/Admin/Social)
- priority (e.g. 1–5)
- frog (boolean)
- alignment (Aligned/Partial/Unaligned)
- first_action
- status (Pending/In Progress/Done/Cancelled)
- scheduled_for (date)
- completed_at

### 8.4 Block

- id
- user_id
- date
- start_time
- end_time
- block_type
- assigned_project_id
- assigned_task_ids[]
- actual_usage_notes

### 8.5 Success Pack

- id
- project_id
- guides[]
- peers[]
- supporters[]
- beneficiaries[]
- last_contacted[]

### 8.6 Waiting On Item

- id
- user_id
- description
- person
- related_project_id
- created_at
- last_followup

---

## 9. Integration Plan

### 9.1 Short-Term (V1)

- Minimal/no live integrations.
- Manual input:
  - Events.
  - Tasks.
  - Why.
  - Projects.

### 9.2 Mid-Term (V2)

- Gmail + Microsoft 365 API integration:
  - Fetch emails.
  - Allow “Send to Organiser” action.
- Calendar integration:
  - Read-only at first.
  - Show events in Today/Week view.

### 9.3 Long-Term (V3+)

- Bi-directional calendar sync.
- Teams/Slack integration:
  - Convert messages to tasks.
- AI assistance for:
  - Classification.
  - Summarisation.
  - Draft replies aligned with Richard’s tone.

---

## 10. Roadmap

### v0.1 – Strong Prototype (this spec)

- Core data models implemented.
- Today/Week/Projects views.
- Morning & Evening flows.
- Task Intake Copilot (manual entry).
- Steady Coach touchpoints (basic).

### v0.2 – Fit & Feel

- Visual polish.
- Performance tuning.
- Small usability improvements.
- Refined prompts & ritual flows.

### v0.3 – Weekly Engine

- Full Weekly review flow.
- Basic summaries of alignment and focus usage.

### v0.4 – Health + Fitness

- Health + fitness dashboard with goals and quick logging.
- Diet, weight, fitness, strength, flexibility tracking pages.
- Metrics with charts and combined blood pressure logging.

### v0.5 – Integrations Start

- One calendar integration (read-only).
- Simple Trello import for projects.

### v1.0 – Personally Stable

- Used by Richard as primary organiser.
- Core features stable and reliable.

---

## 11. Glossary & Concept Index

- **Air Sandwich**: Gap between vision and daily reality, filled with obstacles.
- **Best Work**: Work that makes Richard come alive and serves others.
- **Block**: 90–120 min (Focus/Social) or 30–60 min (Admin) container of time.
- **Five Keys**: Intention, Awareness, Boundaries, Courage, Discipline.
- **Five Projects Rule**: Max ~5 projects per time horizon, 4 work + 3 personal weekly cap.
- **Frog**: High-dread task; best swallowed earlier.
- **OPP**: Other People’s Priorities.
- **Success Pack**: Coordinated network of Guides, Peers, Supporters, Beneficiaries.
- **Thrashing**: Emotional and conceptual flailing around important work.
- **Why**: Core purpose, identity, and values that the app keeps front and centre.

---
# End of Massive Blueprint (v0.1)
