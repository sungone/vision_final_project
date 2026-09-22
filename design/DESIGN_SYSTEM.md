# Smart Bolt Vision Program - Visual Design System

> Version: v1.0 design proposal. This document defines visual rules only and does not authorize frontend implementation.

## 1. Design direction

- Industrial dashboard with a clean, reliable, and inspection-focused tone.
- Hyundai-inspired navy and blue are used as the core identity without reproducing a corporate product UI.
- Light content surfaces improve scanability while the dark navigation rail anchors the workspace.
- Color never replaces text: OK, NG, waiting, and service state must always include a label.

## 2. Color tokens

| Role | Token | Hex | Usage |
| --- | --- | --- | --- |
| Brand navy | `brand-900` | `#002C5F` | Sidebar, mobile header |
| Brand navy active | `brand-700` | `#0B477B` | Selected navigation |
| Primary blue | `primary-600` | `#0075C9` | Main actions, focus, chart line |
| Cyan accent | `accent-500` | `#00A9CE` | Brand mark, progress, measurement overlay |
| Canvas | `surface-canvas` | `#F4F7FA` | Page background |
| Card | `surface-card` | `#FFFFFF` | Cards and panels |
| Soft surface | `surface-soft` | `#F3F7FB` | Inputs, secondary groups, image frames |
| Border | `border-default` | `#D9E4EE` | Card and control borders |
| Text primary | `text-primary` | `#172A3A` | Titles and values |
| Text secondary | `text-secondary` | `#697D90` | Descriptions and metadata |
| OK | `status-ok` | `#168B5B` | Normal inspection and connected state |
| NG | `status-ng` | `#D94B4B` | Defect result and destructive emphasis |
| Warning | `status-warning` | `#D68A18` | Waiting or caution state |

## 3. Typography

- Font stack: Pretendard Variable, Pretendard, Noto Sans KR, Arial, sans-serif.
- Page title: 30 px / 700 desktop, 22 px / 700 mobile.
- Section title: 20 px / 700 desktop, 17 px / 700 mobile.
- Body: 16 px desktop, 14 px mobile.
- Caption and metadata: 13 px desktop, 11 px mobile.
- Large inspection judgment and KPI values use 700-800 weight for quick scanning.

## 4. Layout and components

- Desktop reference frame: 1600 x 900 design canvas, scalable to the 1920 x 1080 target.
- Desktop sidebar: 250 px. Main content begins after a 36 px gutter.
- Mobile reference frame: 430 x 932. Primary actions remain full-width or paired equally.
- Card radius: 10-12 px. Control radius: 6-9 px. Status badge radius: pill shape.
- Core spacing scale: 8, 12, 16, 22, 28, 32 px.
- Primary button: blue fill with white label.
- Secondary button: white or soft surface with visible border and dark label.
- Destructive action: pale red surface or red text; final deletion requires confirmation during implementation.

## 5. Inspection states

| State | Visual treatment |
| --- | --- |
| OK | Green label and pale green badge |
| NG | Red label, pale red summary panel, and red-highlighted selected item |
| Inspecting | Blue progress indicator and explicit status text |
| Waiting | Amber label and explicit queue position |
| Failed | Red label with a retry action and readable error reason |

## 6. Accessibility and responsive rules

- Maintain a minimum 4.5:1 contrast ratio for body text where practical.
- Do not communicate inspection status by color alone.
- Keyboard focus must use a visible blue outline in implementation.
- Desktop comparison panels become a vertical stack on narrow screens.
- Mobile prioritizes capture, upload, result judgment, and previous/next navigation.
- Tables may scroll horizontally on small screens; inspection status and filename remain visible first.

## 7. Scope boundary

The mockups include agreed target-state dashboard, history, batch, camera, storage, and service-status views. These remain design proposals until the Spring Boot and vision-service API contracts are approved.
