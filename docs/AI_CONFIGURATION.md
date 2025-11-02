# AI Configuration Guide

Complete guide for configuring AI-powered code reviews using Claude in the review pipeline.

## Overview

The AI review system uses Claude to perform semantic code analysis across multiple dimensions:
- **Security Review**: OWASP vulnerabilities, authentication flaws, data exposure
- **Architecture Review**: SOLID principles, design patterns, layer violations
- **Code Quality Review**: Complexity, maintainability, readability
- **Performance Review**: Algorithm efficiency, N+1 queries, caching opportunities
- **Testing Review**: Coverage completeness, edge cases, test quality

Unlike static analysis tools that check syntax and patterns, AI reviews understand context, intent, and semantic correctness.

## Quick Start

### Basic Setup

1. **Get Claude API Key**: [Anthropic Console](https://console.anthropic.com/)
2. **Add to GitHub Secrets**: Repository Settings → Secrets → `ANTHROPIC_API_KEY`
3. **Enable in workflow**:

```yaml
jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      enable-ai-review: true
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

That's it! AI reviews will automatically run on all PRs.

## Review Aspects

### 1. Security Review

**Purpose**: Identify security vulnerabilities and unsafe patterns

**Focus Areas**:
- SQL injection, XSS, CSRF vulnerabilities
- Authentication and authorization flaws
- Sensitive data exposure (passwords, API keys in code)
- Insecure cryptography
- Input validation gaps
- OWASP Top 10 issues

**Prompt Template**: [`prompts/security-review.md`](../prompts/security-review.md)

**Example Finding**:
```json
{
  "severity": "critical",
  "category": "security",
  "message": "SQL injection vulnerability: user input concatenated into query",
  "file": "src/api/users.py",
  "line": 42,
  "suggestion": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
}
```

### 2. Architecture Review

**Purpose**: Ensure architectural consistency and design quality

**Focus Areas**:
- SOLID principles violations
- Layer separation (presentation, business, data)
- Circular dependencies
- Inappropriate coupling
- Missing abstractions
- Design pattern misuse

**Prompt Template**: [`prompts/architecture-review.md`](../prompts/architecture-review.md)

**Example Finding**:
```json
{
  "severity": "high",
  "category": "architecture",
  "message": "Business logic found in controller layer",
  "file": "src/controllers/payment.py",
  "line": 28,
  "suggestion": "Move payment processing logic to PaymentService class"
}
```

### 3. Code Quality Review

**Purpose**: Assess maintainability, readability, and code smells

**Focus Areas**:
- Code complexity (cognitive load)
- Code duplication
- Naming conventions
- Function/class size
- Error handling completeness
- Code smells (God objects, feature envy, etc.)

**Prompt Template**: [`prompts/base-review.md`](../prompts/base-review.md)

**Example Finding**:
```json
{
  "severity": "medium",
  "category": "code_quality",
  "message": "Function is 85 lines long and handles multiple responsibilities",
  "file": "src/utils/processor.py",
  "line": 12,
  "suggestion": "Extract validation, transformation, and persistence into separate functions"
}
```

### 4. Performance Review

**Purpose**: Identify performance bottlenecks and inefficiencies

**Focus Areas**:
- N+1 query problems
- Inefficient algorithms (O(n²) where O(n) possible)
- Missing database indexes
- Unnecessary network calls
- Memory leaks
- Missing caching opportunities

**Prompt Template**: [`prompts/performance-review.md`](../prompts/performance-review.md)

**Example Finding**:
```json
{
  "severity": "high",
  "category": "performance",
  "message": "N+1 query detected: fetching related data in loop",
  "file": "src/services/order.py",
  "line": 56,
  "suggestion": "Use eager loading: Order.query.options(joinedload(Order.items)).all()"
}
```

### 5. Testing Review

**Purpose**: Evaluate test coverage and quality

**Focus Areas**:
- Missing tests for new functionality
- Edge case coverage
- Test quality (weak assertions, poor naming)
- Test isolation issues
- Missing integration tests
- Flaky test patterns

**Prompt Template**: [`prompts/testing-review.md`](../prompts/testing-review.md)

**Example Finding**:
```json
{
  "severity": "medium",
  "category": "testing",
  "message": "New payment processing function lacks tests for error cases",
  "file": "src/services/payment.py",
  "line": 42,
  "suggestion": "Add tests for: insufficient funds, invalid card, network timeout"
}
```

## Configuration

### Enable/Disable Review Aspects

Control which AI reviews run in `.github/ai-review-config.yml`:

```yaml
review_aspects:
  - name: security_review
    enabled: true
    type: ai
    prompt_file: prompts/security-review.md
    parallel: false  # Sequential execution

  - name: architecture_review
    enabled: true
    type: ai
    prompt_file: prompts/architecture-review.md
    parallel: false

  - name: code_quality_review
    enabled: true
    type: ai
    prompt_file: prompts/base-review.md
    parallel: false

  - name: performance_review
    enabled: false  # Disable if not needed
    type: ai
    prompt_file: prompts/performance-review.md
    parallel: false

  - name: testing_review
    enabled: true
    type: ai
    prompt_file: prompts/testing-review.md
    parallel: false
```

### Sequential vs Parallel Execution

**Sequential** (recommended for AI reviews):
- Reviews run one after another
- Later reviews can see findings from earlier reviews
- Provides better context and reduces duplication
- Slightly slower but higher quality

**Parallel**:
- Reviews run simultaneously
- Faster execution
- No context sharing between reviews
- May produce duplicate findings

```yaml
review_aspects:
  # Classical tools can run in parallel
  - name: python_static_analysis
    parallel: true

  # AI reviews benefit from sequential execution
  - name: security_review
    parallel: false
```

## Policy Injection

### Company-Level Policies

Inject organization-wide standards into AI prompts.

**Setup**:
1. Create `company-policies.yml` in a central repository
2. Reference in workflow:

```yaml
with:
  company-config-url: 'github://your-org/policies/main/code-review.yml'
```

**Example** ([`examples/company-policies.yml`](../examples/company-policies.yml)):
```yaml
coding_standards:
  python:
    - "Use type hints for all function signatures"
    - "Maximum function length: 50 lines"
    - "All public APIs must have docstrings"

  javascript:
    - "Use TypeScript for all new code"
    - "Prefer async/await over promises"

security_requirements:
  - "All API endpoints must have authentication"
  - "Input validation required for user-provided data"
  - "Secrets must be stored in environment variables"
  - "Database queries must use parameterized statements"

architectural_rules:
  - "Backend must not import from frontend"
  - "Business logic only in service layer"
  - "Direct database access only through repositories"
```

**How It Works**:
The system injects these policies into AI prompts:
```
## Company Coding Standards
You must verify compliance with these organization-wide standards:

### Python
- Use type hints for all function signatures
- Maximum function length: 50 lines
- All public APIs must have docstrings

### Security Requirements
- All API endpoints must have authentication
- Input validation required for user-provided data
[...continues...]

Flag any violations as HIGH severity.
```

### Project-Level Constraints

Add project-specific rules in `.github/ai-review-config.yml`:

```yaml
project_context:
  name: "Payment Processing Service"
  architecture: "Microservices with Event Sourcing"
  critical_paths:
    - "src/payment/"
    - "src/transaction_log/"

project_constraints:
  - "All payment operations must be idempotent"
  - "Transaction amounts must use Decimal, not float"
  - "All database operations must be within transactions"
  - "Financial calculations require audit logging"
  - "Payment failures must trigger compensating transactions"
```

These constraints are injected into every AI review, ensuring context-aware analysis.

## Custom Prompts

### Creating Custom Review Aspects

Create a new review aspect with custom prompts:

1. **Create prompt file** (`prompts/compliance-review.md`):
```markdown
You are a compliance expert reviewing code for regulatory requirements.

## Review Focus
- GDPR compliance (personal data handling)
- Data retention policies
- Audit trail completeness
- Consent management

## Context
{PROJECT_CONTEXT}

## Code Changes
{PR_DIFF}

## Instructions
Identify any compliance issues and respond in JSON format:
[... prompt continues ...]
```

2. **Enable in configuration**:
```yaml
review_aspects:
  - name: compliance_review
    enabled: true
    type: ai
    prompt_file: prompts/compliance-review.md
    parallel: false
```

### Prompt Engineering Best Practices

1. **Be Specific**: Clear instructions produce better results
2. **Provide Context**: Include project architecture and constraints
3. **Request Structured Output**: Always ask for JSON format
4. **Include Examples**: Show desired output format
5. **Set Severity Guidelines**: Define what constitutes critical/high/medium/low

**Good Prompt Structure**:
```markdown
You are a [ROLE] reviewing [WHAT] for [PURPOSE].

## Review Focus
- [Specific area 1]
- [Specific area 2]

## Company Policies
{COMPANY_POLICIES}

## Project Context
{PROJECT_CONTEXT}

## Code Changes
{PR_DIFF}

## Instructions
[Clear, specific instructions]

## Output Format
```json
{
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "security|performance|architecture|quality|testing|documentation",
      "message": "Clear description",
      "file": "path/to/file.py",
      "line": 42,
      "suggestion": "Actionable fix suggestion"
    }
  ]
}
```
```

## Cost Management

### API Usage

Claude API costs vary by model and usage:
- **Claude 3.5 Sonnet**: ~$3 per million input tokens, ~$15 per million output tokens
- **Typical PR review**: 5,000-20,000 tokens (~$0.02-0.30 per PR)

### Optimization Strategies

1. **Analyze Changed Files Only**:
```yaml
with:
  analyze-changed-files-only: true
```

2. **Limit Review Aspects**: Disable unnecessary reviews
```yaml
review_aspects:
  - name: performance_review
    enabled: false  # Skip if not critical
```

3. **Filter by File Patterns**: Skip non-critical files
```yaml
file_filters:
  exclude:
    - "**/*.md"
    - "**/*.txt"
    - "tests/**"
```

4. **Use Smaller Context**: Reduce diff size in prompts
```yaml
ai_config:
  max_context_lines: 500
  include_unchanged_context: false
```

### Cost Examples

**Small Team (10 PRs/day)**:
- 10 PRs × $0.10 average = $1/day
- Monthly cost: ~$30

**Medium Team (50 PRs/day)**:
- 50 PRs × $0.10 average = $5/day
- Monthly cost: ~$150

**Large Team (200 PRs/day)**:
- 200 PRs × $0.10 average = $20/day
- Monthly cost: ~$600

## Advanced Configuration

### Context Sharing

Enable sequential reviews to share context:

```yaml
ai_config:
  enable_context_sharing: true
  context_depth: 3  # How many previous reviews to include
```

**Benefits**:
- Reduces duplicate findings
- Provides richer context to later reviews
- Improves overall quality

### Retry Logic

Configure retry behavior for API failures:

```yaml
ai_config:
  max_retries: 3
  retry_delay: 2  # seconds
  timeout: 120  # seconds per review
```

### JSON Validation

The system automatically validates and retries malformed AI responses:

```yaml
ai_config:
  strict_json_validation: true
  max_correction_attempts: 2
```

If AI returns invalid JSON:
1. System detects error
2. Sends correction prompt with error details
3. AI retries with valid JSON
4. Falls back to text output if correction fails

## Troubleshooting

### Issue: AI Reviews Take Too Long

**Solution**: Reduce context size
```yaml
ai_config:
  max_context_lines: 300
  analyze_changed_files_only: true
```

### Issue: Too Many False Positives

**Solution**: Tune prompts and add project context
```yaml
project_constraints:
  - "Ignore console.log in development files"
  - "Test files can exceed normal line limits"
```

### Issue: Inconsistent Results

**Solution**: Use temperature control
```yaml
ai_config:
  temperature: 0.3  # Lower = more consistent (default: 0.7)
```

### Issue: API Rate Limiting

**Solution**: Add delays or use caching
```yaml
ai_config:
  rate_limit_delay: 1  # second between requests
  enable_response_cache: true
```

### Issue: Security Concerns with Code Exposure

**Solution**: Use self-hosted AI or sanitize diffs
```yaml
ai_config:
  sanitize_diffs: true  # Remove secrets before sending
  exclude_patterns:
    - "*.env"
    - "secrets.yml"
```

## Best Practices

1. **Start with One Aspect**: Enable security review first, add others gradually
2. **Tune with Feedback**: Adjust prompts based on false positive rate
3. **Use Sequential Execution**: Better results than parallel for AI reviews
4. **Inject Context**: Always provide project architecture and constraints
5. **Monitor Costs**: Track API usage, especially for large teams
6. **Document Suppressions**: Explain why you ignore specific findings
7. **Combine with Static Analysis**: AI complements, doesn't replace classical tools

## Working Examples

### Example 1: Fintech Application

See [`examples/project-config.yml`](../examples/project-config.yml) for complete configuration:

```yaml
project_context:
  name: "Trading Platform"
  architecture: "Event-Driven Microservices"
  critical_paths:
    - "src/trading_engine/"
    - "src/risk_management/"

review_aspects:
  - name: security_review
    enabled: true  # Critical for financial data

  - name: architecture_review
    enabled: true  # Maintain event-sourcing patterns

  - name: performance_review
    enabled: true  # Latency is critical

project_constraints:
  - "All financial calculations must use Decimal type"
  - "Trades must be idempotent"
  - "All API calls must have timeout and retry logic"
  - "Risk calculations must be auditable"
```

### Example 2: Public API Service

```yaml
project_context:
  name: "Public REST API"
  architecture: "RESTful API with rate limiting"

review_aspects:
  - name: security_review
    enabled: true

  - name: performance_review
    enabled: true

  - name: testing_review
    enabled: true  # Public APIs need thorough testing

project_constraints:
  - "All endpoints must have rate limiting"
  - "Input validation required on all parameters"
  - "API responses must be paginated"
  - "Breaking changes require version bump"
```

## Integration with Other Tools

### Combine with Static Analysis

AI reviews work best alongside classical tools:

```yaml
# Fast classical checks run first (parallel)
review_aspects:
  - name: python_static_analysis
    enabled: true
    type: classical
    parallel: true

  - name: javascript_static_analysis
    enabled: true
    type: classical
    parallel: true

# AI reviews run after (sequential)
  - name: security_review
    enabled: true
    type: ai
    parallel: false

  - name: architecture_review
    enabled: true
    type: ai
    parallel: false
```

**Result**: Classical tools catch syntax/pattern issues fast, AI reviews provide semantic analysis.

## Next Steps

1. Start with security review only
2. Add project constraints for better context
3. Review findings and tune prompts
4. Gradually enable other review aspects
5. Set up company-level policies for consistency
6. Monitor costs and optimize as needed

## Additional Resources

- [Python Integration Guide](PYTHON_INTEGRATION.md)
- [JavaScript Integration Guide](JAVASCRIPT_INTEGRATION.md)
- [Java Integration Guide](JAVA_INTEGRATION.md)
- [Prompt Templates](../prompts/)
- [Configuration Examples](../examples/)
- [Anthropic Documentation](https://docs.anthropic.com/)
