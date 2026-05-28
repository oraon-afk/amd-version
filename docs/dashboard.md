# Dashboard Module Structure

## Main Dashboard

The dashboard is the primary product surface. It should support repeated operational use by compliance teams.

```text
Dashboard
  Upload workspace
  Audit status timeline
  Risk summary
  Violations and missing clauses table
  Evidence viewer
  Audit report panel
  Upload and audit history
```

## Recommended Layout

```text
Header:
  product name, active organization, user menu

Sidebar:
  Dashboard
  Audits
  Rules
  Settings

Main:
  Left column:
    upload panel
    audit history

  Center column:
    violations table
    finding detail panel

  Right column:
    evidence viewer
    report panel
```

## Finding Detail View

Each finding should show:

```text
finding type
severity
risk level
confidence score
violated or missing rule
rule citation
document evidence citation
grounded explanation
recommendation
```

## Evidence Viewer

Evidence should be traceable:

```text
Rule source
  rule document
  page number
  section title
  snippet

Uploaded document source
  filename
  page number
  text span
  snippet
```

