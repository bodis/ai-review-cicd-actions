# AI-Driven Code Review System - Requirements & Specifications

## Table of Contents
1. [System Overview](#system-overview)
2. [Functional Requirements](#functional-requirements)
3. [Non-Functional Requirements](#non-functional-requirements)
4. [Component Architecture](#component-architecture)
5. [Review Aspects & Best Practices](#review-aspects--best-practices)
6. [Change Type Detection](#change-type-detection)
7. [Injection System](#injection-system)
8. [Validation Matrix](#validation-matrix)
9. [Extension Points](#extension-points)

---

## System Overview

**Purpose:** A generalized, reusable GitHub Actions-based code review system combining classical static analysis with AI-driven intelligent review, supporting multi-language projects with customizable company and project-level policies.

**Core Principles:**
- Centralized maintenance, distributed usage
- Fail-safe defaults (block on uncertainty)
- Layered review (fast checks first, deep analysis later)
- Structured, parseable outputs
- Rich PR feedback with inline comments

---

## Functional Requirements

### FR-1: Core Review Engine
- **FR-1.1** Execute multiple review aspects in configurable order (parallel or sequential)
- **FR-1.2** Support both classical tools (linters, static analyzers) and AI-driven reviews
- **FR-1.3** Aggregate results from all review aspects into unified output
- **FR-1.4** Generate structured JSON output with standardized schema
- **FR-1.5** Validate JSON output with automatic retry on malformed responses

### FR-2: AI Integration
- **FR-2.1** Integrate Claude Code CLI with non-interactive mode (`--yes` flag)
- **FR-2.2** Support multiple AI prompts for different review aspects
- **FR-2.3** Implement prompt engineering for structured output (JSON)
- **FR-2.4** Handle AI rate limits and API errors gracefully
- **FR-2.5** Provide context sharing between sequential AI reviews

### FR-3: GitHub Integration
- **FR-3.1** Trigger on pull request events (opened, synchronize, reopened)
- **FR-3.2** Post summary comment on PR with aggregated findings
- **FR-3.3** Post inline comments on specific lines for critical/high severity issues
- **FR-3.4** Update PR status checks (pass/fail)
- **FR-3.5** Block merge based on configurable severity thresholds
- **FR-3.6** Support GitHub branch protection rules

### FR-4: Change Analysis
- **FR-4.1** Detect changed files in PR (diff analysis)
- **FR-4.2** Identify change types (architecture drift, breaking changes, security risks)
- **FR-4.3** Calculate change impact scores
- **FR-4.4** Filter reviews based on changed file patterns
- **FR-4.5** Detect dependency changes (package.json, requirements.txt, etc.)

### FR-5: Multi-Language Support
- **FR-5.1** Python: Ruff, Pylint, Bandit, mypy support
- **FR-5.2** JavaScript/TypeScript: ESLint, Prettier, TSC support
- **FR-5.3** Language-agnostic AI reviews
- **FR-5.4** Auto-detect languages from changed files
- **FR-5.5** Configure per-language review rules

### FR-6: Configuration System
- **FR-6.1** Load project-level configuration from repository
- **FR-6.2** Load company-level configuration from external source
- **FR-6.3** Merge configurations with proper precedence (project > company > default)
- **FR-6.4** Support YAML/JSON configuration formats
- **FR-6.5** Validate configuration schema

### FR-7: Injection System
- **FR-7.1** Inject company-level policies (coding standards, security requirements)
- **FR-7.2** Inject project-level constraints (architectural rules, test coverage minimums)
- **FR-7.3** Support remote configuration loading (GitHub raw URLs, API endpoints)
- **FR-7.4** Version control for injected configurations
- **FR-7.5** Allow configuration overrides at project level

### FR-8: Result Management
- **FR-8.1** Deduplicate findings across multiple review aspects
- **FR-8.2** Categorize findings by severity (critical, high, medium, low, info)
- **FR-8.3** Categorize findings by type (security, performance, architecture, style, testing)
- **FR-8.4** Generate actionable suggestions for each finding
- **FR-8.5** Track finding history across PR updates

---

## Non-Functional Requirements

### NFR-1: Performance
- **NFR-1.1** Complete review within 5 minutes for typical PR (<500 lines changed)
- **NFR-1.2** Support parallel execution of independent review aspects
- **NFR-1.3** Cache dependencies and tools between runs
- **NFR-1.4** Optimize AI context size to minimize token usage

### NFR-2: Reliability
- **NFR-2.1** Graceful degradation on partial failures (continue other reviews)
- **NFR-2.2** Retry logic for transient failures (network, API limits)
- **NFR-2.3** Fallback to safe defaults on configuration errors
- **NFR-2.4** Comprehensive error logging for debugging

### NFR-3: Security
- **NFR-3.1** Never log or expose API keys in workflow output
- **NFR-3.2** Validate external configuration sources before loading
- **NFR-3.3** Sanitize PR content before sending to AI (remove secrets)
- **NFR-3.4** Use GitHub Secrets for sensitive configuration

### NFR-4: Maintainability
- **NFR-4.1** Modular architecture with clear separation of concerns
- **NFR-4.2** Well-documented APIs for each component
- **NFR-4.3** Comprehensive test coverage (unit + integration)
- **NFR-4.4** Versioned releases with semantic versioning

### NFR-5: Usability
- **NFR-5.1** Clear, actionable error messages
- **NFR-5.2** Rich PR feedback with emojis and formatting
- **NFR-5.3** Minimal setup for consuming projects (1 file, 1 secret)
- **NFR-5.4** Comprehensive documentation with examples

---

## Component Architecture

### Core Components

#### 1. Orchestrator (`lib/orchestrator.py`)
**Purpose:** Coordinates execution of all review aspects

**Functions:**
- `run_review_pipeline(config, pr_context)` - Main entry point
- `execute_review_aspects(aspects, strategy)` - Execute aspects in parallel/sequential
- `aggregate_results(results)` - Merge results from all aspects
- `apply_blocking_rules(findings, config)` - Determine if PR should be blocked
- `generate_summary(findings)` - Create human-readable summary

#### 2. PR Context Builder (`lib/pr_context.py`)
**Purpose:** Extract and prepare PR information for review

**Functions:**
- `get_pr_metadata()` - Get PR title, description, author, labels
- `get_changed_files()` - List all changed files with stats
- `get_pr_diff()` - Get complete diff for changed files
- `detect_languages()` - Identify languages used in changed files
- `detect_change_types()` - Classify changes (feature, bugfix, refactor, etc.)
- `calculate_change_impact()` - Assess scope and risk of changes

#### 3. Classical Analyzers (`lib/analyzers/`)
**Purpose:** Execute traditional linting and static analysis tools

**Modules:**
- `python_analyzer.py` - Ruff, Pylint, Bandit, mypy integration
- `javascript_analyzer.py` - ESLint, Prettier integration
- `typescript_analyzer.py` - TSC, ESLint integration
- `base_analyzer.py` - Abstract base for all analyzers

**Common Functions:**
- `setup_tool()` - Install and configure tool
- `run_analysis(files)` - Execute analysis on changed files
- `parse_results()` - Convert tool output to standard format
- `map_severity()` - Map tool severity to standard levels

#### 4. AI Review Engine (`lib/ai_review.py`)
**Purpose:** Execute AI-driven code reviews using Claude

**Functions:**
- `run_claude_review(prompt, context, max_retries)` - Execute Claude Code with validation
- `build_review_prompt(aspect, pr_context, config)` - Construct AI prompt
- `validate_json_output(output, schema)` - Validate and parse AI response
- `retry_with_correction(error, attempt)` - Retry with JSON correction prompt
- `share_context_between_reviews(results)` - Build context for sequential reviews

#### 5. Change Detector (`lib/change_detector.py`)
**Purpose:** Identify architectural and breaking changes

**Functions:**
- `detect_architecture_drift(diff, baseline)` - Compare against architectural rules
- `detect_breaking_changes(diff, semver_rules)` - Identify API/interface changes
- `detect_security_risks(diff, patterns)` - Scan for security-sensitive changes
- `detect_test_changes(diff)` - Identify test additions/removals
- `detect_dependency_changes(diff)` - Track dependency updates

#### 6. Configuration Manager (`lib/config_manager.py`)
**Purpose:** Load and merge multi-level configurations

**Functions:**
- `load_project_config(path)` - Load from project repository
- `load_company_config(source)` - Load from remote/external source
- `load_default_config()` - Built-in defaults
- `merge_configs(layers)` - Merge with proper precedence
- `validate_config(config, schema)` - Ensure valid configuration
- `resolve_config_references(config)` - Expand variables and imports

#### 7. Injection System (`lib/injection.py`)
**Purpose:** Inject company and project-level rules into prompts

**Functions:**
- `inject_company_policies(prompt, policies)` - Add company standards
- `inject_project_constraints(prompt, constraints)` - Add project rules
- `load_injection_source(source)` - Fetch from remote/local
- `validate_injection_content(content)` - Security check injected content
- `render_template(template, injections)` - Merge injections into prompts

#### 8. Result Aggregator (`lib/aggregator.py`)
**Purpose:** Combine and deduplicate findings

**Functions:**
- `deduplicate_findings(findings)` - Remove duplicate issues
- `categorize_findings(findings)` - Group by severity/category
- `prioritize_findings(findings, rules)` - Sort by importance
- `generate_statistics(findings)` - Count by severity/category
- `filter_findings(findings, filters)` - Apply project-specific filters

#### 9. GitHub Reporter (`lib/github_reporter.py`)
**Purpose:** Post results back to GitHub PR

**Functions:**
- `post_summary_comment(pr, summary)` - Main PR comment
- `post_inline_comments(pr, findings)` - Line-specific comments
- `update_status_check(pr, status)` - Pass/fail status
- `format_finding_message(finding)` - Rich formatting with emojis
- `create_review_event(pr, findings)` - GitHub review API

#### 10. Prompt Library (`prompts/`)
**Purpose:** Reusable AI prompts for different aspects

**Files:**
- `base-review.md` - Generic code quality review
- `security-review.md` - Security-focused review
- `architecture-review.md` - Architectural consistency check
- `performance-review.md` - Performance and efficiency analysis
- `testing-review.md` - Test coverage and quality review

---

## Review Aspects & Best Practices

### 1. Security Review
**Focus Areas:**
- SQL injection vulnerabilities
- XSS (Cross-Site Scripting) risks
- Authentication/authorization flaws
- Sensitive data exposure (API keys, passwords in code)
- Insecure dependencies (known CVEs)
- CORS misconfigurations
- Input validation gaps

**Best Practices:**
- Always parameterize database queries
- Sanitize user inputs before use
- Use environment variables for secrets
- Implement principle of least privilege
- Keep dependencies updated
- Enable CSP (Content Security Policy) headers

**AI Prompt Focus:**
```
Review for security vulnerabilities including:
- Authentication bypass opportunities
- Data validation gaps
- Secret exposure risks
- Known vulnerable patterns (OWASP Top 10)
```

### 2. Architecture Review
**Focus Areas:**
- Adherence to established patterns (MVC, Clean Architecture, etc.)
- Separation of concerns violations
- Tight coupling between modules
- Missing abstraction layers
- Inappropriate dependencies
- Architectural drift from baseline

**Best Practices:**
- Follow SOLID principles
- Maintain clear module boundaries
- Use dependency injection
- Keep business logic separate from infrastructure
- Document architectural decisions (ADRs)

**AI Prompt Focus:**
```
Analyze architectural consistency:
- Does this maintain separation of concerns?
- Are there new cross-cutting concerns?
- Does it follow the project's architectural pattern?
- Are there signs of technical debt accumulation?
```

### 3. Code Quality Review
**Focus Areas:**
- Code complexity (cyclomatic complexity)
- Code duplication (DRY violations)
- Naming conventions
- Function/method length
- Error handling completeness
- Code readability

**Best Practices:**
- Keep functions under 50 lines
- Use descriptive variable names
- Avoid magic numbers
- Handle all error cases
- Add comments for complex logic
- Maintain consistent style

**AI Prompt Focus:**
```
Evaluate code quality:
- Is this code readable and maintainable?
- Are there duplicated patterns that could be abstracted?
- Are variable/function names clear and descriptive?
- Is error handling comprehensive?
```

### 4. Performance Review
**Focus Areas:**
- N+1 query problems
- Inefficient algorithms (O(n²) where O(n) possible)
- Missing indexes on database queries
- Unnecessary network calls
- Memory leaks
- Unoptimized loops

**Best Practices:**
- Use appropriate data structures
- Implement caching where beneficial
- Batch database operations
- Paginate large result sets
- Profile before optimizing
- Avoid premature optimization

**AI Prompt Focus:**
```
Identify performance concerns:
- Are there potential N+1 query issues?
- Could algorithms be more efficient?
- Are there unnecessary computations?
- Is caching used appropriately?
```

### 5. Testing Review
**Focus Areas:**
- Test coverage for new code
- Test quality (meaningful assertions)
- Missing edge case tests
- Flaky test patterns
- Test isolation issues
- Missing integration tests

**Best Practices:**
- Aim for >80% coverage on new code
- Test both happy paths and error cases
- Use descriptive test names
- Keep tests independent
- Mock external dependencies
- Include integration tests for critical paths

**AI Prompt Focus:**
```
Assess testing completeness:
- Are there tests for the new functionality?
- Are edge cases covered?
- Are error conditions tested?
- Would additional tests increase confidence?
```

### 6. Documentation Review
**Focus Areas:**
- Missing docstrings/JSDoc
- Outdated documentation
- Complex logic without comments
- Missing README updates
- API documentation gaps
- Changelog entries

**Best Practices:**
- Document public APIs
- Explain "why" not just "what"
- Update docs with code changes
- Include usage examples
- Maintain changelog

**AI Prompt Focus:**
```
Check documentation needs:
- Are new functions/classes documented?
- Do complex sections need clarification?
- Are there API changes requiring doc updates?
```

---

## Change Type Detection

### Architecture Drift Detection
**Indicators:**
- New dependencies violating layering rules
- Direct database access from presentation layer
- Business logic in controllers/views
- Circular dependencies introduced

**Detection Method:**
```python
def detect_architecture_drift(diff, architecture_rules):
    """
    Compare changes against architectural baseline
    
    Rules example:
    - Backend should not import from frontend
    - Controllers should not contain business logic
    - Database access only through repository layer
    """
    violations = []
    for file_change in diff:
        layer = identify_layer(file_change.path)
        imports = extract_imports(file_change.content)
        for imp in imports:
            if violates_layering(layer, imp, architecture_rules):
                violations.append(ArchitectureViolation(
                    file=file_change.path,
                    line=imp.line,
                    message=f"Layer {layer} should not import from {imp.module}"
                ))
    return violations
```

### Breaking Change Detection
**Indicators:**
- Modified public API signatures
- Removed public methods/functions
- Changed return types
- Modified database schema
- Renamed configuration variables

**Detection Method:**
```python
def detect_breaking_changes(diff, api_catalog):
    """
    Identify changes that break backward compatibility
    
    Checks:
    - Public function signature changes
    - Removed exports
    - Modified API endpoints
    - Database migration changes
    """
    breaking_changes = []
    for file_change in diff:
        if is_public_api(file_change.path):
            old_api = extract_api(file_change.old_content)
            new_api = extract_api(file_change.new_content)
            changes = compare_apis(old_api, new_api)
            for change in changes:
                if change.is_breaking:
                    breaking_changes.append(change)
    return breaking_changes
```

### Security Risk Detection
**Indicators:**
- New authentication bypass paths
- Relaxed permission checks
- Disabled security features
- Exposed sensitive endpoints
- Weak cryptography usage

**Detection Method:**
```python
def detect_security_risks(diff, security_patterns):
    """
    Scan for security-sensitive changes
    
    Patterns:
    - Authentication decorators removed
    - SQL string concatenation
    - eval() usage
    - Disabled CSRF protection
    """
    risks = []
    for file_change in diff:
        for pattern in security_patterns:
            matches = pattern.find_in(file_change.content)
            for match in matches:
                risks.append(SecurityRisk(
                    file=file_change.path,
                    line=match.line,
                    pattern=pattern.name,
                    severity=pattern.severity
                ))
    return risks
```

### Dependency Change Detection
**Indicators:**
- New dependencies added
- Major version upgrades
- Deprecated dependencies
- Known vulnerable versions

**Detection Method:**
```python
def detect_dependency_changes(diff):
    """
    Track dependency file changes
    
    Files to monitor:
    - requirements.txt, Pipfile, pyproject.toml
    - package.json, yarn.lock
    - go.mod, Cargo.toml
    """
    dep_changes = []
    dependency_files = [
        'requirements.txt', 'package.json', 'go.mod'
    ]
    for file_change in diff:
        if file_change.path in dependency_files:
            old_deps = parse_dependencies(file_change.old_content)
            new_deps = parse_dependencies(file_change.new_content)
            added = new_deps - old_deps
            removed = old_deps - new_deps
            updated = get_version_changes(old_deps, new_deps)
            
            dep_changes.append(DependencyChange(
                file=file_change.path,
                added=added,
                removed=removed,
                updated=updated
            ))
    return dep_changes
```

---

## Injection System

### Company-Level Policy Injection

**Purpose:** Enforce organization-wide standards across all projects

**Structure:**
```yaml
# company-policies.yml
coding_standards:
  python:
    - "Use type hints for all function signatures"
    - "Maximum function length: 50 lines"
    - "All public APIs must have docstrings"
  javascript:
    - "Use ES6+ syntax (no var, use const/let)"
    - "Async operations must use async/await"
  
security_requirements:
  - "All API endpoints must have authentication"
  - "Input validation required for user-provided data"
  - "Secrets must be stored in environment variables"
  - "Database queries must use parameterized statements"

architectural_rules:
  - "Backend must not import from frontend"
  - "Business logic only in service layer"
  - "Direct database access only through repositories"

documentation_requirements:
  - "All public APIs require documentation"
  - "Complex algorithms need explanatory comments"
  - "Update CHANGELOG.md for user-facing changes"
```

**Loading Mechanism:**
```python
def load_company_policies(source):
    """
    Load company-level policies from external source
    
    Sources supported:
    - GitHub raw URL: github://org/repo/path/file.yml
    - HTTP URL: https://company.com/policies/code-review.yml
    - S3: s3://bucket/policies/review.yml
    """
    if source.startswith('github://'):
        return fetch_from_github(source)
    elif source.startswith('http'):
        return fetch_from_url(source)
    elif source.startswith('s3://'):
        return fetch_from_s3(source)
    else:
        raise ValueError(f"Unknown source type: {source}")

def inject_into_prompt(base_prompt, policies):
    """
    Inject company policies into AI prompt
    """
    policy_text = format_policies(policies)
    return base_prompt.replace(
        '{COMPANY_POLICIES}',
        f"""
## Company Coding Standards
You must verify compliance with these organization-wide standards:

{policy_text}

Flag any violations as HIGH severity.
"""
    )
```

### Project-Level Constraint Injection

**Purpose:** Apply project-specific rules and context

**Structure:**
```yaml
# .github/ai-review-config.yml (in project repo)
project_context:
  name: "Payment Processing Service"
  architecture: "Microservices with Event Sourcing"
  critical_paths:
    - "backend/payment_processor/"
    - "backend/transaction_log/"

project_constraints:
  - "All payment operations must be idempotent"
  - "Transaction amounts must use Decimal, not float"
  - "All database operations must be within transactions"
  - "Financial calculations require audit logging"

review_focus:
  high_priority:
    - "Security in payment handling"
    - "Data consistency in transactions"
  low_priority:
    - "UI styling changes"
    - "Documentation updates"

custom_rules:
  - pattern: "float.*amount|price|total"
    message: "Use Decimal for monetary values, not float"
    severity: "critical"
  
  - pattern: "execute\\(.*\\+ .*\\)|cursor\\.execute\\(f\""
    message: "SQL injection risk: use parameterized queries"
    severity: "critical"
```

**Injection Process:**
```python
def build_review_prompt(aspect, pr_context, config):
    """
    Build AI prompt with all injections
    """
    # Load base prompt
    base_prompt = load_prompt_template(f"prompts/{aspect}-review.md")
    
    # Inject company policies
    if config.company_policies_source:
        policies = load_company_policies(config.company_policies_source)
        base_prompt = inject_into_prompt(base_prompt, policies)
    
    # Inject project constraints
    if config.project_constraints:
        base_prompt = inject_project_constraints(
            base_prompt,
            config.project_constraints
        )
    
    # Add project context
    context_text = f"""
## Project Context
- Name: {config.project_context.name}
- Architecture: {config.project_context.architecture}
- Critical Paths: {', '.join(config.project_context.critical_paths)}

When reviewing changes in critical paths, be extra thorough.
"""
    base_prompt = base_prompt.replace('{PROJECT_CONTEXT}', context_text)
    
    # Inject custom rules
    if config.custom_rules:
        rules_text = format_custom_rules(config.custom_rules)
        base_prompt += f"\n## Project-Specific Rules\n{rules_text}"
    
    # Finally, inject PR content
    base_prompt = base_prompt.replace('{PR_DIFF}', pr_context.diff)
    base_prompt = base_prompt.replace('{CHANGED_FILES}', pr_context.files)
    
    return base_prompt
```

### Injection Precedence

**Order of Application:**
1. **Default/Built-in Rules** (lowest priority)
2. **Company-Level Policies** (medium priority)
3. **Project-Level Constraints** (highest priority)

**Conflict Resolution:**
- Project-level rules can **override** company-level rules
- Must explicitly declare override in project config
- Conflicts are logged for audit

```yaml
# Project config with override
project_constraints:
  - rule: "Maximum function length: 100 lines"
    overrides: "company_policy:max_function_length"
    justification: "Complex financial calculations require longer functions"
```

---

## Validation Matrix

### Table 1: Classical Analysis Validations

| Aspect | Language | Tool | What It Checks | Severity Levels | Blocking |
|--------|----------|------|----------------|-----------------|----------|
| **Code Style** | Python | Ruff | PEP 8 compliance, import sorting, line length | low, info | No |
| **Code Style** | JavaScript | ESLint | Formatting, naming conventions, unused vars | low, medium | Configurable |
| **Code Style** | JavaScript | Prettier | Code formatting consistency | info | No |
| **Static Analysis** | Python | Pylint | Code smells, complexity, maintainability | low, medium, high | On high |
| **Type Checking** | Python | mypy | Type hint violations, type safety | medium, high | On high |
| **Type Checking** | TypeScript | TSC | TypeScript compilation, type errors | high | Yes |
| **Security** | Python | Bandit | Security vulnerabilities, insecure patterns | medium, high, critical | On critical |
| **Security** | JavaScript | ESLint (security plugins) | XSS, injection risks, insecure dependencies | high, critical | On critical |
| **Complexity** | All | radon (Python) | Cyclomatic complexity, maintainability index | medium | No |
| **Dependencies** | All | Safety (Python), npm audit | Known CVEs in dependencies | high, critical | On critical |
| **Coverage** | All | Coverage.py, Istanbul | Test coverage percentage | info, low | Configurable |
| **Duplication** | All | jscpd | Code duplication detection | low, medium | No |

### Table 2: AI-Driven Review Validations

| Aspect | Focus Area | Key Checks | Typical Severity | Blocking |
|--------|------------|------------|------------------|----------|
| **Security Review** | Authentication | Missing auth checks, bypass opportunities | critical, high | Yes |
| **Security Review** | Input Validation | Unsanitized inputs, injection risks | critical, high | Yes |
| **Security Review** | Data Exposure | Sensitive data in logs, API responses | high | Yes |
| **Security Review** | Cryptography | Weak algorithms, hardcoded keys | critical | Yes |
| **Architecture Review** | Layering | Layer violations, circular dependencies | high, medium | On high |
| **Architecture Review** | Separation of Concerns | Business logic in wrong layer | medium | No |
| **Architecture Review** | Design Patterns | Pattern misuse, anti-patterns | low, medium | No |
| **Architecture Review** | Dependencies | Inappropriate dependencies added | medium, high | On high |
| **Code Quality** | Readability | Unclear naming, complex expressions | low, medium | No |
| **Code Quality** | Maintainability | Long functions, deep nesting | medium | No |
| **Code Quality** | Error Handling | Missing try-catch, unhandled errors | high | Yes |
| **Code Quality** | Code Smells | God objects, feature envy, shotgun surgery | low, medium | No |
| **Performance** | Algorithms | Inefficient algorithms, O(n²) loops | medium, high | No |
| **Performance** | Database | N+1 queries, missing indexes | high | No |
| **Performance** | Caching | Missing cache opportunities | low | No |
| **Performance** | Memory | Potential memory leaks, large allocations | medium | No |
| **Testing** | Coverage | Missing tests for new code | medium | Configurable |
| **Testing** | Quality | Weak assertions, poor test names | low | No |
| **Testing** | Edge Cases | Missing error case tests | medium | No |
| **Documentation** | API Docs | Missing docstrings, unclear signatures | low, medium | No |
| **Documentation** | Comments | Complex logic without explanation | low | No |

### Table 3: Change Type Detections

| Detection Type | Indicators | Severity | Automatic Actions |
|----------------|------------|----------|-------------------|
| **Architecture Drift** | Layer violations, new dependencies crossing boundaries | high | Flag for architect review, block merge |
| **Breaking Change** | Modified public APIs, removed exports, schema changes | high | Require semver major bump, extensive testing |
| **Security Risk** | Relaxed permissions, disabled security features | critical | Block merge, require security team review |
| **Performance Regression** | New N+1 queries, inefficient algorithms in hot paths | medium | Flag for performance testing |
| **Test Coverage Drop** | New code without tests, removed tests | medium | Request test additions |
| **Dependency Risk** | Major version upgrades, deprecated packages, CVEs | high | Check changelog, run compatibility tests |
| **Database Change** | Schema migrations, index changes | high | Require DBA review, rollback plan |
| **API Change** | Modified endpoints, changed request/response | medium | Update API documentation, notify consumers |

---

## Extension Points

### Recommended Extensions (Priority Order)

#### 1. **Enhanced Static Analysis**
**Description:** Add more language-specific analyzers
- **Go:** golangci-lint, go vet, staticcheck
- **Rust:** Clippy, rustfmt, cargo-audit
- **Java:** SpotBugs, PMD, Checkstyle
- **C#:** Roslyn analyzers, SonarAnalyzer
- **Ruby:** RuboCop, Brakeman
- **PHP:** PHPStan, Psalm

**Integration Pattern:**
```python
class GoAnalyzer(BaseAnalyzer):
    def run_analysis(self, files):
        results = []
        results.extend(self.run_golangci_lint(files))
        results.extend(self.run_go_vet(files))
        return self.standardize_results(results)
```

#### 2. **Semantic Diff Analysis**
**Description:** Understand code changes at AST level, not just text diff
- Parse code into Abstract Syntax Trees
- Detect refactorings (renamed variables, extracted methods)
- Identify actual logic changes vs formatting changes
- Reduce false positives from formatter changes

**Use Case:** Distinguish between "functionally identical refactor" and "logic change"

#### 3. **Historical Context Learning**
**Description:** Learn from past PR reviews to improve accuracy
- Track which findings were marked "false positive"
- Build project-specific issue database
- Adjust severity based on historical acceptance
- Suggest fixes based on how similar issues were resolved

**Implementation:**
```python
def learn_from_review_history(pr_number):
    """
    Analyze past reviews to improve future suggestions
    """
    past_findings = load_past_pr_findings(project_id)
    false_positives = filter_dismissed_findings(past_findings)
    
    # Adjust confidence scores
    for pattern in false_positives:
        reduce_pattern_severity(pattern)
    
    # Learn accepted fix patterns
    accepted_fixes = get_accepted_fixes(past_findings)
    update_suggestion_templates(accepted_fixes)
```

#### 4. **Auto-Fix Suggestions**
**Description:** Generate code patches for simple issues
- Auto-format code style issues
- Suggest imports for missing dependencies
- Generate boilerplate (docstrings, type hints)
- Create test stubs for new functions

**GitHub Integration:**
```yaml
- name: Generate auto-fixes
  run: |
    python generate_fixes.py > fixes.patch
    
- name: Create suggestion commits
  run: |
    git apply fixes.patch
    git commit -m "AI-suggested fixes"
    gh pr comment --body "I've prepared some auto-fixes in this branch"
```

#### 5. **Compliance Checking**
**Description:** Verify regulatory compliance requirements
- GDPR: Check for personal data handling
- HIPAA: Verify healthcare data protection
- PCI-DSS: Ensure payment data security
- SOC 2: Validate audit logging

**Configuration:**
```yaml
compliance_frameworks:
  - gdpr:
      checks:
        - personal_data_encryption
        - consent_verification
        - right_to_deletion
  - pci_dss:
      checks:
        - payment_data_isolation
        - no_card_numbers_in_logs
```

#### 6. **License Compatibility Checking**
**Description:** Verify dependency licenses don't conflict
- Scan new dependencies for license types
- Check compatibility with project license
- Warn on copyleft licenses in proprietary code
- Generate license attribution files

#### 7. **Performance Benchmarking**
**Description:** Run automated performance tests on PR changes
- Detect performance regressions
- Compare against baseline metrics
- Run load tests for API changes
- Profile memory usage

**Integration:**
```yaml
- name: Performance test
  if: contains(github.event.pull_request.labels.*.name, 'performance-critical')
  run: |
    python benchmark.py --baseline main --compare HEAD
    python analyze_results.py > perf-report.md
```

#### 8. **Visual Regression Testing**
**Description:** Detect unintended UI changes
- Screenshot comparison for frontend changes
- Pixel-diff analysis
- Accessibility testing (WCAG compliance)
- Cross-browser compatibility checks

#### 9. **Documentation Generation**
**Description:** Auto-generate documentation from code
- API documentation from OpenAPI specs
- Docstring generation for undocumented code
- Architecture diagrams from dependencies
- Changelog entries from commit messages

#### 10. **Cross-Repository Impact Analysis**
**Description:** Analyze impact on dependent projects
- Find repos that depend on changed APIs
- Notify affected teams
- Suggest migration paths
- Run integration tests against dependents

**Use Case:** Microservices architecture with shared libraries

#### 11. **Smart Test Selection**
**Description:** Run only tests affected by changes
- Analyze code coverage data
- Map changes to test files
- Run only relevant tests (faster CI)
- Detect missing test coverage

#### 12. **Deployment Risk Scoring**
**Description:** Assign risk score to each PR
- Based on changed files (critical paths = higher risk)
- Complexity of changes
- Historical bug rate in changed areas
- Require more reviewers for high-risk PRs

**Risk Matrix:**
```
Low Risk: Documentation, tests, UI styling
Medium Risk: New features, refactoring
High Risk: Authentication, payment processing, database schema
Critical Risk: Security features, core business logic
```

#### 13. **Internationalization (i18n) Checks**
**Description:** Ensure proper i18n implementation
- Detect hardcoded strings that should be translated
- Verify translation keys exist
- Check for missing translations
- Validate placeholders in translated strings

#### 14. **Accessibility (a11y) Review**
**Description:** AI-driven accessibility analysis
- Check for missing alt text
- Verify keyboard navigation
- Validate ARIA labels
- Color contrast checking

#### 15. **Dead Code Detection**
**Description:** Identify unused code
- Find unreferenced functions
- Detect unused imports
- Identify dead branches (always false conditions)
- Flag deprecated API usage

---

## Implementation Checklist

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Set up repository structure
- [ ] Create reusable workflow file
- [ ] Implement orchestrator with parallel/sequential execution
- [ ] Build PR context extractor
- [ ] Implement configuration loader with multi-level support
- [ ] Create JSON schema and validation

### Phase 2: Classical Analyzers (Week 3)
- [ ] Python analyzer (Ruff, Pylint, Bandit, mypy)
- [ ] JavaScript analyzer (ESLint, Prettier)
- [ ] TypeScript analyzer (TSC)
- [ ] Result standardization layer
- [ ] Severity mapping

### Phase 3: AI Integration (Week 4-5)
- [ ] Claude Code CLI wrapper with retry logic
- [ ] Prompt template system
- [ ] JSON validation with auto-correction
- [ ] Context sharing between reviews
- [ ] Company/project injection system

### Phase 4: Change Detection (Week 6)
- [ ] Architecture drift detector
- [ ] Breaking change analyzer
- [ ] Security risk scanner
- [ ] Dependency change tracker

### Phase 5: GitHub Integration (Week 7)
- [ ] Summary comment poster
- [ ] Inline comment creator
- [ ] Status check updater
- [ ] Branch protection integration
- [ ] Result deduplication

### Phase 6: Documentation & Testing (Week 8)
- [ ] Comprehensive README
- [ ] Usage examples
- [ ] Configuration documentation
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests
- [ ] Example project setups

### Phase 7: Extensions (Future)
- [ ] Additional language analyzers
- [ ] Semantic diff analysis
- [ ] Historical learning
- [ ] Auto-fix generation

---

## Success Metrics

**Adoption Metrics:**
- Number of projects using the system
- Number of PRs reviewed per week
- User satisfaction score

**Quality Metrics:**
- False positive rate (<10% target)
- Critical bugs caught in review (vs production)
- Average review completion time (<5 min)

**Impact Metrics:**
- Reduction in production bugs
- Decrease in security vulnerabilities
- Improved code quality scores over time
- Developer time saved on manual reviews

---

## Notes for AI Implementation Assistant

**Key Implementation Considerations:**

1. **Error Handling:** Every component should gracefully handle failures and provide clear error messages

2. **Configurability:** Make thresholds, severity mappings, and blocking rules configurable

3. **Performance:** Use caching extensively, parallelize where possible, optimize AI context size

4. **Security:** Never log secrets, sanitize PR content before sending to AI, validate all external inputs

5. **Testability:** Write modular, testable code with clear interfaces

6. **Documentation:** Include inline comments for complex logic, maintain up-to-date README

7. **Versioning:** Use semantic versioning, maintain changelog, tag releases properly

This specification should provide a complete foundation for implementing a production-grade AI-driven code review system.
