# 💙 Sahay AI

**An AI-powered student wellness companion — a calm, supportive space to reflect, check in, and find real support.**

Sahay AI is a Streamlit web application that combines a conversational AI companion with practical wellness tools — mood check-ins, relaxation activities, self-reported wellness trends, and curated support resources — for students navigating everyday stress. It is **not** a therapist, doctor, or crisis service, and it never claims to be one.

Built for the Edunet Foundation × IBM SkillsBuild "AI for Non-Technical Students" internship, problem statement: *Mental Health Companion Chatbot*.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat&logo=supabase&logoColor=white)
![AI](https://img.shields.io/badge/AI-OpenRouter-8B85C1?style=flat)

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Application Pages](#application-pages)
4. [AI Companion & Safety Pipeline](#ai-companion--safety-pipeline)
5. [Technology Stack](#technology-stack)
6. [System Architecture](#system-architecture)
7. [Application Navigation](#application-navigation)
8. [Project Structure](#project-structure)
9. [Streamlit App-Shell Configuration](#streamlit-app-shell-configuration)
10. [Installation & Setup](#installation--setup)
11. [Database Setup](#database-setup)
12. [Authentication & Demo Mode](#authentication--demo-mode)
13. [Reports & Data Export](#reports--data-export)
14. [Privacy & Safety](#privacy--safety)
15. [Admin Panel](#admin-panel)
16. [Current Project Status](#current-project-status)
17. [Potential Future Work](#potential-future-work)

---

## Overview

Sahay AI gives students a low-pressure place to talk through what's on their mind, notice patterns in how they've been feeling, and find the right kind of help when they want more than a chat — whether that's a breathing exercise, a support resource, or a real person.

**Who it's for:** students dealing with the ordinary pressures of academic life — exam stress, procrastination, sleep, loneliness, motivation — who want a private, judgment-free space to check in with themselves.

**What AI does here:** a conversational companion (built on a large language model via OpenRouter) that responds supportively to what a student shares, offers a non-clinical mood signal, and occasionally suggests a relevant wellness activity — always screened by a deterministic safety layer that runs independently of the model.

**What Sahay AI is *not*:** it does not diagnose, prescribe, or claim to be a therapist, psychologist, psychiatrist, or doctor, and it does not replace professional or emergency care. If a student is in immediate danger, the app's Human Help page is designed to point them to real emergency and support channels — Sahay AI does not attempt to handle the situation itself.

## Key Features

| Feature | What it does |
|---|---|
| 💬 **Sahay Companion** | Full conversational chat with persisted history (signed-in users), grouped by Today / Yesterday / Older, with rename, delete, and clear-conversation controls |
| 🎈 **Floating Companion** | A lightweight, always-available chat widget on every dashboard page — session-only, independent of the persisted Companion history |
| 🙂 **Mood Check-in** | Mood picker plus optional stress / energy / sleep self-rating scales and a free-text note |
| 📈 **Mood History** | Chronological list of past mood entries with distribution and trend charts; per-entry deletion |
| 📊 **Wellness Dashboard** | At-a-glance activity summary — conversation counts, mood check-ins, mood distribution, self-reported wellness trends |
| 🧘 **Relaxation Center** | Eight guided wellness activities with step-by-step instructions and completion tracking |
| 🗂️ **Conversations** | Dedicated list view of every saved conversation, linking back into the full Companion |
| 📚 **Support Resources** | Ten practical, non-clinical guides for common student experiences |
| 🇮🇳 **Government & Student Support Services** | Plain-language explanations of relevant support programs, with official links where verified |
| 🤝 **Human Help** | Tiered support: everyday people to talk to, urgent-danger guidance, and a crisis-resources section that only ever shows verified information |
| 📄 **Reports** | Downloadable Wellness Reflection Report (PDF or DOCX) over a selectable 7/14/30-day window |
| 👤 **Profile** | Manage display name and preferred chat language |
| 🔒 **Privacy Controls** | Plain-language data explanation, plus self-service deletion of conversation and mood history |
| ⚙️ **Settings** | Dark mode toggle and a feedback submission form |
| 🎭 **Demo Mode** | Explore the full app with no account — nothing typed in Demo Mode is saved anywhere |
| 🔐 **Authentication** | Email/password sign-up and login, password reset, and Google sign-in, all via Supabase Auth |
| 🛡️ **Admin Panel** | A separate, isolated dashboard for administrators — never linked from student navigation |

## Application Pages

| Page | Purpose | Main Capabilities |
|---|---|---|
| **Overview** | Home dashboard | At-a-glance activity snapshot and a quick way into the Companion |
| **Sahay Companion** | Full AI chat experience | Persisted, multi-conversation chat history; rename/delete; per-turn mood signal; wellness suggestions |
| **Mood Check-in** | Log how you're feeling | Mood picker, optional stress/energy/sleep scales, free-text note |
| **Wellness Dashboard** | Activity summary | Conversation/check-in counts, mood distribution, self-reported trend charts |
| **Relaxation** | Guided wellness activities | 8 activities with instructions and completion tracking |
| **Mood History** | Past mood entries | Chronological list, charts, per-entry deletion |
| **Conversations** | Saved conversation list | Browse and reopen any saved conversation |
| **Support Resources** | Practical guidance | 10 topic guides with tips and links to relevant activities |
| **Government & Student Support Services** | Program information | Plain-language explanations of relevant support programs |
| **Human Help** | Real support pathways | Everyday support contacts, urgent-danger guidance, verified crisis resources |
| **Reports** | Wellness summary export | PDF/DOCX Wellness Reflection Report over a selectable period |
| **Profile** | Account details | Display name and preferred language |
| **Privacy** | Data control | Explanation of data handling; delete conversations or mood history |
| **Settings** | App preferences | Dark mode, feedback submission |

## AI Companion & Safety Pipeline

The Companion is designed to be calm, supportive, and non-judgmental — a space to talk through how your day or week is going, not a diagnostic tool.

**Provider:** conversational responses and mood classification are generated through **OpenRouter**, a unified API gateway for large language models (`backend/openrouter_client.py`). The default model, configurable via the `OPENROUTER_MODEL` environment variable, is `openai/gpt-4o-mini`.

Every chat turn runs through a single, fixed pipeline (`chatbot/response_generator.py::generate_response()`), so no other code path can call the AI provider directly or skip a safety step:

1. **Input safety screening** (`chatbot/safety.py`) — deterministic, pattern-based checks that run *before* the model is ever called, independent of the LLM itself.
2. **Mood analysis** (`chatbot/mood_analyzer.py`) — a non-clinical signal (e.g. "Calm," "Anxious," "Stressed") derived from the message. This is explicitly documented in the code as an *application-level signal, never a medical diagnosis*.
3. **Response generation** — the OpenRouter call itself, guided by a system prompt (`chatbot/system_prompt.py`) instructing the model not to diagnose, prescribe, or claim a professional identity.
4. **Output safety screening** — a final check on the model's reply before it reaches the user.

If `OPENROUTER_API_KEY` isn't configured, the app degrades gracefully to a clearly-labeled placeholder reply instead of failing — it never silently pretends to be connected.

Signed-in users get a full, persisted conversation history; the floating Companion widget available on every dashboard page is a lighter, session-only quick-chat, deliberately not wired to that persisted history.

## Technology Stack

### Frontend / Application
| Technology | Role |
|---|---|
| [Streamlit](https://streamlit.io/) | Application framework — renders every page, form, and widget |
| Custom CSS design tokens (`components/theme.py`) | Consistent visual system — color, radius, shadow, typography, light/dark mode |

### AI
| Technology | Role |
|---|---|
| [OpenRouter](https://openrouter.ai/) | LLM API gateway for the Companion's conversational responses and mood classification (default model: `openai/gpt-4o-mini`) |

### Backend / Database
| Technology | Role |
|---|---|
| [Supabase](https://supabase.com/) (Postgres) | Stores conversations, messages, mood events, wellness activity logs, profiles, feedback, and safety events |
| Supabase Row Level Security (RLS) | Enforces per-user data isolation at the database level |

### Authentication
| Technology | Role |
|---|---|
| Supabase Auth | Email/password sign-up, login, password reset |
| Google OAuth (via Supabase Auth) | Optional "Continue with Google" sign-in |
| bcrypt | Password hashing for the separate, independent admin-account system |

### Reporting
| Technology | Role |
|---|---|
| [fpdf2](https://github.com/py-pdf/fpdf2) | Generates the PDF Wellness Reflection Report |
| [python-docx](https://python-docx.readthedocs.io/) | Generates the DOCX Wellness Reflection Report |

### Deployment
| Technology | Role |
|---|---|
| Streamlit (any Streamlit-compatible host) | Hosting |
| `.streamlit/config.toml` | Suppresses Streamlit's default multipage navigation/toolbar in favor of Sahay's own custom UI |

## System Architecture

```
                          Student
                             │
                             ▼
                 Streamlit Application (streamlit_app.py)
                 · auth gate  · admin gate  · custom page router
                             │
              ┌──────────────┼──────────────┐
              ▼                             ▼
   Custom Navigation                 Admin Shell
   (components/sidebar.py,           (admin/*, isolated
    topbar.py, chatbot_launcher.py)   session, own login)
              │
              ▼
        Pages & Components
   (pages/*.py — one render() per page,
    components/cards.py, components/page_components/*)
              │
     ┌────────┼─────────────┐
     ▼                      ▼
AI Services            Backend / Data Layer
(chatbot/*  →           (backend/auth.py,
 safety screening →      backend/conversations.py,
 mood analysis →         backend/admin_*.py)
 OpenRouter call)               │
                                 ▼
                        Supabase (Postgres + Auth)
                        RLS-scoped per user
```

## Application Navigation

Sahay AI does **not** use Streamlit's native file-based multipage routing. All 14 user-facing modules under `pages/` are plain Python files, each exposing a single `render()` function — they are wired together entirely by the application's own custom router, not by Streamlit's automatic page discovery.

`streamlit_app.py` maintains a `PAGE_RENDERERS` dictionary mapping a page key (e.g. `"overview"`, `"companion"`) to that page's `render` function. The currently active page is tracked in `st.session_state["sahay_page"]`, set by the custom sidebar (`components/sidebar.py`) whenever a navigation item is clicked, and dispatched each rerun via `PAGE_RENDERERS[current_page]()`. An import-time `assert` cross-checks `PAGE_RENDERERS`'s keys against `components/sidebar.py`'s `ALL_PAGE_KEYS`, so the two can't silently drift apart.

The sidebar itself is a custom off-canvas drawer (fixed positioning, open/closed via `st.session_state["sahay_sidebar_open"]`), and the floating Companion widget is a separately fixed-position container — both built entirely in Streamlit/CSS, with no client-side routing framework involved.

## Project Structure

```
sahay-ai/
├── streamlit_app.py            # Entry point: auth gate, admin gate, custom page router
├── config.py                   # Centralized env/secrets loader
├── requirements.txt
├── .streamlit/
│   ├── config.toml             # Hides Streamlit's default nav/toolbar chrome
│   └── secrets.toml.example    # Template for local secrets — copy, never commit
│
├── pages/                      # One file per user-facing page, each exposing render()
│   ├── overview.py
│   ├── companion.py
│   ├── mood_checkin.py
│   ├── wellness_dashboard.py
│   ├── relaxation.py
│   ├── mood_history.py
│   ├── conversations.py
│   ├── resources.py
│   ├── government_services.py
│   ├── human_help.py
│   ├── reports.py
│   ├── profile.py
│   ├── privacy.py
│   └── settings.py
│
├── components/                 # Shared, presentation-only UI building blocks
│   ├── theme.py                 # Design tokens + global CSS injection
│   ├── sidebar.py                # Custom collapsible navigation drawer
│   ├── topbar.py                 # Page header bar
│   ├── landing.py                 # Public landing page (auth forms)
│   ├── cards.py                   # metric_card, accent_card, empty_state, safety_note
│   ├── chatbot_launcher.py         # Floating Companion widget
│   └── page_components/            # page_header, section_header, list_row, confirm_action
│
├── backend/                    # Supabase-facing service layer
│   ├── auth.py                    # Sign-up/in, OAuth, sessions, profile
│   ├── conversations.py            # Conversation/message/mood/activity CRUD
│   ├── supabase_client.py           # Anon-key (RLS-scoped) client
│   ├── supabase_admin_client.py      # Service-role client (admin-only)
│   ├── admin_auth.py                  # Independent admin login system
│   ├── admin_data.py                   # Admin aggregate queries
│   ├── audit_log.py                     # Admin action logging
│   └── openrouter_client.py              # Low-level OpenRouter HTTP client
│
├── chatbot/                    # The AI conversation pipeline
│   ├── safety.py                  # Deterministic input/output safety screening
│   ├── mood_analyzer.py            # Non-clinical mood/sentiment classification
│   ├── system_prompt.py             # Companion's system prompt
│   └── response_generator.py         # Orchestrates a single chat turn
│
├── admin/                      # Isolated administrator panel
│   ├── login.py
│   ├── shell.py
│   └── views.py
│
├── content/                    # Static, editable factual content
│   ├── government_services.py
│   └── crisis_resources.py        # Populated only with verified sources
│
├── exports/                    # Report generation
│   ├── _shared.py                 # Report data shaping (library-independent)
│   ├── pdf.py
│   └── docx.py
│
├── database/migrations/        # Versioned SQL migrations (Supabase/Postgres)
├── utils/                      # Formatting and validation helpers
└── tests/                      # Mock-backed test suite
```

## Streamlit App-Shell Configuration

`.streamlit/config.toml` sets two Streamlit client options:

```toml
[client]
showSidebarNavigation = false
toolbarMode = "minimal"
```

- **`showSidebarNavigation = false`** disables the native sidebar page list Streamlit would otherwise auto-generate from the `pages/` directory — since Sahay AI has its own custom navigation (see [Application Navigation](#application-navigation)), that native list is not used.
- **`toolbarMode = "minimal"`** reduces Streamlit's built-in header toolbar (menu, deploy/share controls).

This configuration only affects Streamlit's own default chrome. It has no effect on, and cannot remove, any chrome added by a hosting provider around the app itself (for example, a platform-level "manage app" control on Streamlit Community Cloud) — that lives outside the application and is not something this project can control.

## Installation & Setup

### Requirements
- Python 3.10+
- A Supabase project (optional — the app runs without one, in Demo Mode only)
- An OpenRouter API key (optional — without one, the Companion shows a placeholder reply instead of a generated one)

### Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd sahay-ai

# 2. Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets (optional — the app runs fully in Demo Mode without this)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit .streamlit/secrets.toml with your own values

# 5. Run the app
streamlit run streamlit_app.py
```

### Configuration reference

All values below are read from `.streamlit/secrets.toml` (local) or your host's secrets manager, and every one is optional — the app runs with none of them configured, in Demo Mode.

```toml
APP_NAME = "Sahay AI"
COMPANION_NAME = "Sahay"
APP_ENV = "development"

# Supabase Auth + user data
SUPABASE_URL = "your_value"
SUPABASE_ANON_KEY = "your_value"

# Google OAuth (optional "Continue with Google")
GOOGLE_OAUTH_CLIENT_ID = "your_value"
GOOGLE_OAUTH_REDIRECT_URL = "your_value"

# AI engine (OpenRouter)
OPENROUTER_API_KEY = "your_value"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "openai/gpt-4o-mini"

# Admin panel only — service-role key, NEVER expose to the browser or commit it
SUPABASE_SERVICE_ROLE_KEY = "your_value"
```

## Database Setup

Sahay AI's persisted data (conversations, messages, mood events, wellness activity logs, profiles, feedback, safety events, and admin accounts) lives in a Supabase Postgres project, defined by 13 versioned SQL migrations in `database/migrations/`. If you're connecting a real Supabase project, apply these in order (`001_initial_schema.sql` through `013_safety_events.sql`) via the Supabase SQL editor before first use. Row Level Security policies (`002`, `008`) are part of this migration set and enforce that each signed-in user can only read or write their own rows.

No database is required to explore the app in Demo Mode.

## Authentication & Demo Mode

Sahay AI supports two ways to use the app:

- **Signed in** — via email/password or Google, through Supabase Auth. Signed-in users get real, private, persisted data: saved conversations, mood history, wellness activity logs, and a profile, all scoped to that user by Supabase Row Level Security.
- **Demo Mode** — a no-account preview accessible directly from the landing page. Demo Mode never calls Supabase: the Companion chat, mood check-ins, and activity completions all live only in the browser session and are lost when the session ends.

The **Admin Panel** is a third, completely separate system — see [Admin Panel](#admin-panel).

## Reports & Data Export

The Reports page builds a **Wellness Reflection Report** summarizing recent activity — conversation counts, mood check-ins, and completed activities — over a period you choose (7, 14, or 30 days). It is available as a **PDF** (via fpdf2) or **DOCX** (via python-docx) download.

- **Signed-in users** get a real report built from their actual persisted data, always bounded to the selected period — never an unlimited history export.
- **Demo Mode** generates a clearly-labeled *sample* report from the current session's chat only; nothing is read from or written to Supabase.

## Privacy & Safety

Sahay AI is built around a few explicit principles, reflected directly in the app:

- **Data isolation** — every signed-in user's data is scoped to that user via Supabase Row Level Security, enforced at the database level.
- **User-controlled deletion** — the Privacy page lets a signed-in user permanently delete all saved conversations or all mood history, each behind an explicit confirm/cancel step.
- **Transparent data handling** — the Privacy page plainly explains what is and isn't stored, and why mood signals are kept.
- **No fabricated safety information** — the crisis-resources section only ever displays verified, explicitly added entries; if none are populated yet, it says so honestly rather than showing a placeholder.
- **A distinct urgent-support tier** — the Human Help page visually separates "someone to talk to" from "immediate danger" guidance.
- **Independent safety screening** — chat safety checks run as fixed, deterministic logic outside the language model.

Sahay AI does **not** claim to be fully secure, fully anonymous, or medically safe, and has not undergone an independent third-party security audit or any formal compliance certification (e.g. HIPAA, GDPR). It relies on Supabase's authentication and Row Level Security for data protection.

## Admin Panel

Administrators reach a separate dashboard via a `?admin=1` URL parameter — it is **never** linked from student-facing navigation. The admin system:

- authenticates independently of Supabase Auth, via a dedicated `admin_users` table and bcrypt password hashing (`backend/admin_auth.py`);
- has its own session state, entirely isolated from any student session;
- provides a dashboard, user list, feedback review, safety-event log, and system view (`admin/views.py`);
- has no code path reachable from a student account, and the floating Companion widget is never rendered inside it.

There is no public admin sign-up flow. The first admin account must be created directly in the database — see the project's migration documentation for the exact steps.

## Current Project Status

Sahay AI's frontend has gone through a staged, LearnMate-inspired visual redesign, implemented and reviewed in phases. As of this README:

| Area | Status |
|---|---|
| Design system (theme, tokens) | Implemented |
| Landing page | Implemented |
| User dashboard shell (sidebar, topbar) | Implemented |
| Floating Companion widget | Implemented |
| All 13 non-Companion user pages | Implemented |
| Sahay Companion page redesign | **Implemented, pending final review/approval** |
| Streamlit app-shell chrome cleanup | Implemented |

The Companion page's visual redesign has been implemented in the codebase but had not yet received final explicit sign-off at the time of this README — it should not be read as a fully closed-out, approved milestone the way the other listed items are. Core functionality (authentication, conversation persistence, AI pipeline, safety screening, database operations) is implemented and unaffected by this distinction, which concerns presentation/UI review status only.

## Potential Future Work

The following are **not implemented** — they are ideas noted for possible future consideration, not existing functionality:

- Expanding the verified crisis-resources list (currently intentionally empty pending verified sources)
- Additional relaxation activities
- Broader analytics for the admin dashboard
- Automated end-to-end test coverage beyond the current mock-backed test suite

---

Sahay AI is a student wellness support tool, not a medical device or licensed healthcare service. It does not diagnose, treat, or prescribe, and it is not a substitute for professional medical, psychological, or emergency care. If you or someone you know is in immediate danger, please contact local emergency services right away.
