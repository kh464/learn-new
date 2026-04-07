# Dual Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a learner-facing frontend and an admin-facing frontend as two separate entries inside the existing Vue + Vite project.

**Architecture:** Keep one `frontend/` project and split it into multi-page entries. The learner app will expose only learning-loop functionality, while the admin app will retain runtime, task, knowledge, export, and checkpoint operations. Shared API calls stay in `frontend/src/lib/api.js`.

**Tech Stack:** Vue 3, Vite multi-page build, FastAPI, pytest

---

### Task 1: Lock The New Frontend Contract With Tests

**Files:**
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_dashboard_route_serves_user_and_admin_entry_notice(...):
    ...
    assert "user.html" in response.text
    assert "admin.html" in response.text

def test_frontend_workspace_exposes_dual_entries(...):
    package_json = Path("frontend/package.json").read_text(encoding="utf-8")
    user_html = Path("frontend/user.html").read_text(encoding="utf-8")
    admin_html = Path("frontend/admin.html").read_text(encoding="utf-8")
    user_main = Path("frontend/src/user-main.js").read_text(encoding="utf-8")
    admin_main = Path("frontend/src/admin-main.js").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py -q`
Expected: FAIL because the current frontend only has one app entry.

- [ ] **Step 3: Write minimal implementation**

Create the dual-entry files and update dashboard copy to match the new contract.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dashboard.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_dashboard.py frontend app/dashboard.py
git commit -m "test: lock dual frontend entry contract"
```

### Task 2: Split Frontend Into Learner And Admin Apps

**Files:**
- Create: `frontend/user.html`
- Create: `frontend/admin.html`
- Create: `frontend/src/user-main.js`
- Create: `frontend/src/admin-main.js`
- Create: `frontend/src/apps/user/UserApp.vue`
- Create: `frontend/src/apps/admin/AdminApp.vue`
- Create: `frontend/src/components/user/*.vue`
- Move/Modify: `frontend/src/components/*.vue`
- Modify: `frontend/src/lib/api.js`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing test**

Use the Task 1 contract tests as the red signal for missing dual-entry structure.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py::test_frontend_vue_workspace_exists_with_vite_proxy_and_components -q`
Expected: FAIL because `user.html` and `admin.html` are absent.

- [ ] **Step 3: Write minimal implementation**

Split the current `App.vue` responsibilities:

- learner app keeps session selection, sync turn, lesson, feedback, mastery, timeline
- admin app keeps operational components and admin-key handling
- shared request helpers remain centralized

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dashboard.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend tests/test_dashboard.py
git commit -m "feat: split frontend into learner and admin entries"
```

### Task 3: Update Runtime Entry Docs And Startup Guidance

**Files:**
- Modify: `README.md`
- Modify: `docs/frontend-dashboard.md`
- Modify: `frontend/README.md`
- Modify: `app/dashboard.py`

- [ ] **Step 1: Write the failing test**

Extend dashboard notice assertions to require `user.html` and `admin.html`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py::test_dashboard_route_serves_frontend_split_notice -q`
Expected: FAIL if the notice page still describes only one frontend.

- [ ] **Step 3: Write minimal implementation**

Document:

- user frontend URL
- admin frontend URL
- which audience each entry serves
- how to start Vite once and open the right page

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dashboard.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md docs/frontend-dashboard.md frontend/README.md app/dashboard.py tests/test_dashboard.py
git commit -m "docs: explain learner and admin frontend split"
```

### Task 4: Full Verification

**Files:**
- Modify: none unless verification exposes failures

- [ ] **Step 1: Run backend tests**

Run: `pytest tests -q`
Expected: PASS

- [ ] **Step 2: Run frontend production build**

Run: `npm run build`
Workdir: `frontend/`
Expected: PASS and emit both learner/admin pages into `dist/`

- [ ] **Step 3: Check git status**

Run: `git status --short`
Expected: only intended tracked changes remain

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: separate learner and admin frontends"
```
