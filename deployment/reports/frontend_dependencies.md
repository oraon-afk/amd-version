# Frontend Dependencies

## Files Analyzed

- `frontend/package.json`
- `frontend/package-lock.json`
- No `pnpm-lock.yaml` detected.
- No `yarn.lock` detected.

## Detected Runtime Packages

- `next`
- `react`
- `react-dom`
- `@tanstack/react-query`
- `axios`
- `framer-motion`
- `lucide-react`
- `react-hook-form`
- `@hookform/resolvers`
- `zod`
- `recharts`
- `class-variance-authority`
- `clsx`
- `tailwind-merge`

## Detected Build Packages

- `typescript`
- `tailwindcss`
- `@tailwindcss/postcss`
- `postcss`
- `autoprefixer`
- `eslint`
- `eslint-config-next`
- `@types/node`
- `@types/react`
- `@types/react-dom`

## Validation

Commands run:

```bash
npm ls --depth=0
npm ci --dry-run
npm run build
```

Results:

- `npm ls --depth=0`: passed. Some optional/extraneous platform packages are present in local `node_modules`, which is normal for optional native packages.
- `npm ci --dry-run`: passed.
- `npm run build`: passed. Next.js generated 37 app routes successfully.

Warnings:

- Local Node.js was `v22.8.0`.
- `eslint-visitor-keys@5.0.1` requests Node `^20.19.0 || ^22.13.0 || >=24`.
- VM setup should use Node only inside Docker. The frontend container uses `node:20-alpine`, satisfying the package engine range.

## Alias Validation

Imports use the `@/` alias to reference `frontend/src`. No unresolved alias pattern was detected during the production build.
