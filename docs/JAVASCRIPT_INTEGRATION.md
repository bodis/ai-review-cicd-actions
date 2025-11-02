# JavaScript/TypeScript Integration Guide

Complete guide for integrating JavaScript and TypeScript static analysis tools into the AI Code Review pipeline.

## Overview

The pipeline uses multiple JS/TS analysis tools:
- **ESLint**: Linting and code quality for JavaScript/TypeScript
- **Prettier**: Code formatting and style consistency
- **TSC**: TypeScript compiler for type checking
- **Optional**: Additional plugins for React, Node.js, security

## Quick Start

### Minimal Setup

Add to your project's workflow (`.github/workflows/code-review.yml`):

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      enable-js-analysis: true
      node-version: '20'
    secrets:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

The workflow will automatically:
1. Install Node.js and npm packages
2. Run ESLint, Prettier, and TypeScript checks
3. Post findings as PR comments

## Analysis Tools

### 1. ESLint

**Purpose**: Pluggable linting utility for JavaScript and TypeScript

**What it checks:**
- Code quality issues
- Potential bugs
- Stylistic inconsistencies
- Best practices violations
- Security vulnerabilities (with plugins)
- Framework-specific rules (React, Vue, etc.)

**Installation**:
```bash
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

**Configuration** (`.eslintrc.json` or `eslint.config.js`):

```json
{
  "env": {
    "browser": true,
    "es2021": true,
    "node": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module",
    "project": "./tsconfig.json"
  },
  "plugins": [
    "@typescript-eslint"
  ],
  "rules": {
    "no-console": "warn",
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": [
      "error",
      { "argsIgnorePattern": "^_" }
    ],
    "@typescript-eslint/explicit-function-return-type": "warn",
    "prefer-const": "error",
    "no-var": "error"
  }
}
```

**Command line**:
```bash
npx eslint . --ext .js,.jsx,.ts,.tsx
npx eslint . --fix  # Auto-fix issues
```

### 2. Prettier

**Purpose**: Opinionated code formatter

**What it formats:**
- Indentation and spacing
- Line length
- Quotes (single vs double)
- Semicolons
- Trailing commas
- Bracket spacing

**Installation**:
```bash
npm install --save-dev prettier eslint-config-prettier
```

**Configuration** (`.prettierrc.json`):
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

**Ignore file** (`.prettierignore`):
```
node_modules
dist
build
coverage
*.min.js
```

**Command line**:
```bash
npx prettier --check .
npx prettier --write .  # Auto-format
```

### 3. TypeScript Compiler (TSC)

**Purpose**: Type checking and compilation for TypeScript

**What it checks:**
- Type errors
- Type mismatches
- Missing properties
- Incompatible types
- Strict null checks
- Unused locals

**Configuration** (`tsconfig.json`):
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.spec.ts"]
}
```

**Command line**:
```bash
npx tsc --noEmit  # Type check only, no compilation
npx tsc  # Full compilation
```

## Enhanced Configurations

### React Project

**ESLint with React**:
```bash
npm install --save-dev \
  eslint-plugin-react \
  eslint-plugin-react-hooks \
  eslint-plugin-jsx-a11y
```

`.eslintrc.json`:
```json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended"
  ],
  "plugins": [
    "react",
    "react-hooks",
    "jsx-a11y"
  ],
  "settings": {
    "react": {
      "version": "detect"
    }
  },
  "rules": {
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn"
  }
}
```

### Node.js Project

**ESLint for Node.js**:
```json
{
  "env": {
    "node": true,
    "es2021": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "rules": {
    "no-console": "off",
    "no-process-env": "warn"
  }
}
```

### Security Enhanced

**Add security linting**:
```bash
npm install --save-dev eslint-plugin-security
```

`.eslintrc.json`:
```json
{
  "plugins": ["security"],
  "extends": ["plugin:security/recommended"],
  "rules": {
    "security/detect-object-injection": "warn",
    "security/detect-non-literal-regexp": "warn",
    "security/detect-unsafe-regex": "error"
  }
}
```

## Project Configuration

### Basic Configuration

Create `.github/ai-review-config.yml`:

```yaml
# JavaScript/TypeScript configuration
review_aspects:
  - name: javascript_static_analysis
    enabled: true
    type: classical
    tools:
      - eslint
      - prettier
      - tsc
    parallel: true

# Custom rules
custom_rules:
  - pattern: "console\\.log"
    message: "Remove console.log before merging to production"
    severity: "low"

  - pattern: "debugger;"
    message: "Remove debugger statement"
    severity: "medium"

  - pattern: "any(?!where|thing)"
    message: "Avoid using 'any' type in TypeScript"
    severity: "medium"

  - pattern: "eval\\("
    message: "Use of eval() is a security risk"
    severity: "critical"
```

### TypeScript Project Constraints

```yaml
project_constraints:
  - "All functions must have explicit return types"
  - "Use interfaces for object shapes, types for unions/intersections"
  - "Prefer async/await over promises for readability"
  - "All React components must be functional (no class components)"
  - "Use TypeScript strict mode"
```

### React Project Example

```yaml
project_context:
  name: "React Dashboard"
  architecture: "React + TypeScript SPA"
  critical_paths:
    - "src/components/Auth/"
    - "src/services/api/"

project_constraints:
  - "All API calls must include error handling"
  - "Use React Query for server state management"
  - "Components must be smaller than 300 lines"
  - "Avoid inline styles, use CSS modules or styled-components"
  - "All user inputs must be validated"

custom_rules:
  - pattern: "useState\\<any\\>"
    message: "Avoid 'any' type in useState hooks"
    severity: "medium"

  - pattern: "useEffect\\(\\(\\) => \\{[^}]*\\}, \\[\\]\\)"
    message: "Verify useEffect dependencies are complete"
    severity: "low"
```

## Working Examples

### Example 1: Next.js Application

See [`examples/nextjs-config.yml`](../examples/nextjs-config.yml):

```yaml
project_context:
  name: "Next.js E-commerce"
  architecture: "Next.js 14 with App Router"

project_constraints:
  - "All API routes must validate input with Zod"
  - "Use Server Components by default, Client Components only when needed"
  - "Images must use next/image component"
  - "All pages must have metadata for SEO"

custom_rules:
  - pattern: "<img"
    message: "Use next/image instead of <img> tag"
    severity: "high"

  - pattern: "\"use client\".*\\n.*import.*next/image"
    message: "next/image works in Server Components, avoid 'use client' if possible"
    severity: "low"
```

### Example 2: Express.js API

Configuration for backend Node.js projects:

```yaml
project_context:
  name: "Express REST API"
  architecture: "RESTful API with Express + TypeScript"

project_constraints:
  - "All routes must have input validation middleware"
  - "Use async/await for asynchronous operations"
  - "All errors must be handled by error middleware"
  - "Database queries must use parameterized statements"

custom_rules:
  - pattern: "app\\.(get|post|put|delete)\\([^,]+, *async"
    message: "Route missing error handling wrapper"
    severity: "high"
```

## Common Issues and Fixes

### Issue: ESLint and Prettier Conflicts

**Problem**: ESLint and Prettier have conflicting formatting rules

**Solution**: Use `eslint-config-prettier`
```bash
npm install --save-dev eslint-config-prettier
```

`.eslintrc.json`:
```json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier"  // Must be last!
  ]
}
```

### Issue: TypeScript Performance Issues

**Problem**: `tsc` is slow on large codebases

**Solution**: Use project references and incremental compilation

`tsconfig.json`:
```json
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": ".tsbuildinfo"
  }
}
```

Or only check changed files:
```yaml
with:
  analyze-changed-files-only: true
```

### Issue: Too Many `any` Type Warnings

**Problem**: Legacy code has many `any` types

**Solution**: Gradually migrate with configuration
```json
{
  "compilerOptions": {
    "noImplicitAny": false  // Start here
  }
}

// Then enable per-directory
{
  "extends": "./tsconfig.json",
  "include": ["src/new-feature/**/*"],
  "compilerOptions": {
    "noImplicitAny": true
  }
}
```

### Issue: ESLint Not Finding TypeScript Files

**Problem**: ESLint ignores `.ts/.tsx` files

**Solution**: Check parser and extensions
```json
{
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": "./tsconfig.json"
  }
}
```

Command:
```bash
npx eslint . --ext .js,.jsx,.ts,.tsx
```

## Integration with IDE

### VS Code

Install extensions:
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- TypeScript (built-in)

Settings (`.vscode/settings.json`):
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true
}
```

### WebStorm

1. Settings → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint
2. Enable "Automatic ESLint configuration"
3. Settings → Languages & Frameworks → JavaScript → Prettier
4. Check "On save" for automatic formatting

## Performance Optimization

### Caching Strategy

```yaml
- name: Cache Node Modules
  uses: actions/cache@v3
  with:
    path: |
      ~/.npm
      node_modules
      .eslintcache
    key: node-${{ hashFiles('**/package-lock.json') }}
```

### ESLint Caching

```bash
npx eslint . --cache --cache-location .eslintcache
```

Add to `.gitignore`:
```
.eslintcache
.tsbuildinfo
```

### Parallel Execution

The pipeline runs tools in parallel automatically:
- ESLint, Prettier, TSC run concurrently
- Reduces analysis time by ~50%

## Best Practices

1. **Use TypeScript Strict Mode**: Enable all strict flags
2. **Integrate Prettier Early**: Avoid formatting debates
3. **Extend Standard Configs**: Build on `eslint:recommended`
4. **Document Rule Changes**: Explain why you disable rules
5. **Keep Dependencies Updated**: Run `npm update` regularly
6. **Use Pre-commit Hooks**: Catch issues before pushing

## Pre-commit Integration

`.husky/pre-commit`:
```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npm run lint
npm run type-check
npm run format:check
```

`package.json`:
```json
{
  "scripts": {
    "lint": "eslint . --ext .js,.jsx,.ts,.tsx",
    "lint:fix": "eslint . --ext .js,.jsx,.ts,.tsx --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "type-check": "tsc --noEmit"
  },
  "devDependencies": {
    "husky": "^8.0.0"
  }
}
```

Install:
```bash
npm install --save-dev husky
npx husky install
```

## Package.json Scripts

Add useful scripts:

```json
{
  "scripts": {
    "lint": "eslint . --ext .js,.jsx,.ts,.tsx",
    "lint:fix": "eslint . --ext .js,.jsx,.ts,.tsx --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "type-check": "tsc --noEmit",
    "check-all": "npm run lint && npm run type-check && npm run format:check"
  }
}
```

## Dependencies

Add to `package.json`:
```json
{
  "devDependencies": {
    "eslint": "^8.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "eslint-config-prettier": "^9.0.0",
    "prettier": "^3.0.0",
    "typescript": "^5.0.0",

    // Optional: React
    "eslint-plugin-react": "^7.33.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-jsx-a11y": "^6.7.0",

    // Optional: Security
    "eslint-plugin-security": "^1.7.0"
  }
}
```

## Troubleshooting

### ESLint Can't Resolve Imports

**Solution**: Configure module resolution
```json
{
  "settings": {
    "import/resolver": {
      "typescript": {
        "project": "./tsconfig.json"
      },
      "node": {
        "extensions": [".js", ".jsx", ".ts", ".tsx"]
      }
    }
  }
}
```

### Prettier Ignores Some Files

**Solution**: Check `.prettierignore` and file extensions
```
# .prettierignore
node_modules
dist
build
*.min.js
```

### TypeScript Can't Find Modules

**Solution**: Check `tsconfig.json` paths and `moduleResolution`
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    },
    "moduleResolution": "bundler"
  }
}
```

## Next Steps

1. Review [AI_CONFIGURATION.md](AI_CONFIGURATION.md) for AI-powered review setup
2. Check [examples/](../examples/) for working configurations
3. See main [README.md](../README.md) for overall architecture

## Resources

- [ESLint Documentation](https://eslint.org/docs/latest/)
- [Prettier Documentation](https://prettier.io/docs/en/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [TypeScript ESLint](https://typescript-eslint.io/)
- [React ESLint Plugin](https://github.com/jsx-eslint/eslint-plugin-react)
- [ESLint Security Plugin](https://github.com/eslint-community/eslint-plugin-security)
