# Smart Bolt Vision Program - UI/UX Design Brief

> Status: Color mockup phase. This directory contains design-only artifacts. No frontend or backend implementation is included.

## Relationship to the current MVP

The repository's current MVP is limited to single-image inspection and three public result fields. The dashboard, history, database-backed metrics, batch upload, camera capture, and storage-management views in these wireframes describe the agreed target UI and remain post-MVP design scope until their API and data contracts are approved.

## 1. Product goal

Upload or capture bolt assembly images, automatically inspect every image, and make OK/NG results and MES-style quality trends easy to understand.

## 2. Confirmed requirements

- Desktop-first responsive web UI based on 1920 x 1080.
- Light content area with a dark navy sidebar in the final visual design.
- Chrome is the primary browser.
- Camera capture inspects one image at a time.
- Multi-image, folder, and ZIP uploads run as an automatic batch.
- Supported image formats: JPG, JPEG, PNG.
- Original and annotated result images are retained until manually deleted.
- No sign-in in the initial scope.
- Shared inspection thresholds are read-only.
- Mobile focuses on capture, upload, and result review.
- Text logo first; leave room for a future symbol.

## 3. Navigation

1. Dashboard
2. Image inspection
3. Inspection history
4. Environment settings

Inspection detail is not a permanent sidebar item. It opens from an inspection result, history row, or recent defect card.

## 4. Primary user flow

```text
Dashboard
  -> Image inspection
      -> Capture one image OR upload images/folder/ZIP
      -> Automatic inspection
      -> Result viewer
          -> Previous/next image
          -> Select by filename
          -> Open inspection detail
  -> Inspection history
      -> Filter results
      -> Select a record
      -> Inspection detail
```

## 5. Dashboard metrics

- Total inspections
- OK count and rate
- NG count and defect rate
- Average inspection time
- Average washer-nut gap
- Average exposed thread length
- Average nut tilt angle
- Defects by category
- Inspection volume by time
- Recent defect records

Default period: Today.

## 6. Defect categories

- Missing bolt
- Missing washer
- Missing nut
- Incorrect assembly order
- Tilted nut
- Incorrect fastening position

## 7. Inspection viewer states

- Upload empty state
- Uploading
- Queued
- Inspecting
- OK
- NG
- Failed

## 8. Settings content

- Read-only inspection thresholds
- Local camera selection and permission state
- Supported file types and batch limits
- Storage usage and connection status
- Spring Boot, vision service, and database connection status
- Model name, version, and update date

## 9. Wireframes

- `wireframes/01_dashboard-desktop.svg`
- `wireframes/02_inspection-desktop.svg`
- `wireframes/03_inspection-mobile.svg`
- `wireframes/04_history-desktop.svg`
- `wireframes/05_inspection-detail-desktop.svg`
- `wireframes/06_settings-desktop.svg`

All numbers and records in the wireframes are illustrative placeholders.

## 10. Color mockups

- `mockups/01_dashboard-desktop.svg`
- `mockups/02_inspection-desktop.svg`
- `mockups/03_inspection-mobile.svg`
- `mockups/04_history-desktop.svg`
- `mockups/05_inspection-detail-desktop.svg`
- `mockups/06_settings-desktop.svg`

The color mockups preserve the approved wireframe layouts and apply the shared rules in `DESIGN_SYSTEM.md`. All numbers, records, image areas, and service states remain illustrative placeholders.
