# Platform Abstraction - Implementation Summary

## Overview

The codebase now supports **both GitHub and GitLab** through a clean abstraction layer that separates platform-specific API calls from the core review logic.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     main.py                                  │
│                 (Platform-agnostic)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ├── Auto-detect platform (GitHub/GitLab)
                      │
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              lib/platform/factory.py                         │
│         (Creates appropriate platform instance)             │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴────────────┐
          │                        │
          ↓                        ↓
┌──────────────────┐    ┌──────────────────┐
│ GitHub Platform  │    │ GitLab Platform  │
│                  │    │                  │
│ • PyGithub API   │    │ • python-gitlab  │
│ • PR fetching    │    │ • MR fetching    │
│ • Comments       │    │ • Notes          │
│ • Status checks  │    │ • Discussions    │
└──────────────────┘    └──────────────────┘
          │                        │
          └───────────┬────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────┐
│            lib/platform/base.py                              │
│        (Abstract Interface - CodeReviewPlatform)             │
│                                                              │
│  • get_context(project_id, mr_number) -> PRContext          │
│  • post_summary_comment(project_id, mr_number, comment)     │
│  • post_inline_comments(project_id, mr_number, findings)    │
│  • update_status(project_id, commit_sha, state, desc)       │
└─────────────────────────────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              ReviewOrchestrator                              │
│         (Receives PRContext, platform-agnostic)              │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Abstract Interface (`lib/platform/base.py`)

Defines the contract that all platforms must implement:

```python
class CodeReviewPlatform(ABC):
    @abstractmethod
    def get_context(self, project_identifier: str, mr_number: int) -> PRContext:
        """Fetch MR/PR context"""

    @abstractmethod
    def post_summary_comment(self, project_identifier: str, mr_number: int, comment: str):
        """Post summary comment"""

    @abstractmethod
    def post_inline_comments(self, project_identifier: str, mr_number: int,
                            findings: list[Finding], comment_texts: list[str]):
        """Post inline comments"""

    @abstractmethod
    def update_status(self, project_identifier: str, commit_sha: str,
                     state: str, description: str, context: str):
        """Update commit/pipeline status"""
```

### 2. Platform Implementations

**GitHub** (`lib/platform/github_platform.py`):
- Uses `PyGithub` library
- Implements PR fetching with `get_repo().get_pull()`
- Posts issue comments and review comments
- Updates commit status with `create_status()`

**GitLab** (`lib/platform/gitlab_platform.py`):
- Uses `python-gitlab` library
- Implements MR fetching with `projects.get().mergerequests.get()`
- Posts notes and discussions
- Updates commit status with `commit.statuses.create()`

### 3. Factory Pattern (`lib/platform/factory.py`)

Auto-detects platform and creates appropriate instance:

```python
def detect_platform() -> PlatformType:
    if os.getenv('GITLAB_CI'):
        return 'gitlab'
    elif os.getenv('GITHUB_ACTIONS'):
        return 'github'
    return 'github'  # default

def create_platform(platform_type: PlatformType | None, token: str | None):
    if platform_type == 'github':
        return GitHubPlatform(token)
    elif platform_type == 'gitlab':
        return GitLabPlatform(token)
```

### 4. Platform Reporter (`lib/platform/base.PlatformReporter`)

Abstract reporter class that handles:
- AI-generated summary comments
- Inline comment generation
- Status updates
- Severity filtering

Both `GitHubReporter` and `GitLabReporter` extend this base class.

## Usage

### GitHub (No changes required)

```bash
# Auto-detected when GITHUB_ACTIONS=true
python main.py --repo owner/repo --pr 123
```

### GitLab (New!)

```bash
# Auto-detected when GITLAB_CI=true
python main.py --repo namespace/project --pr 456

# Or explicitly specify platform
python main.py --platform gitlab --repo 12345 --pr 456
```

### Environment Variables

**GitHub**:
- `GITHUB_TOKEN` - Required
- `GITHUB_ACTIONS=true` - Auto-set in GitHub Actions

**GitLab**:
- `CI_JOB_TOKEN` or `GITLAB_TOKEN` - Required
- `CI_SERVER_URL` - GitLab instance URL (default: https://gitlab.com)
- `GITLAB_CI=true` - Auto-set in GitLab CI

**Both**:
- `ANTHROPIC_API_KEY` - Required for AI reviews

## Key API Differences Handled

| Operation | GitHub API | GitLab API | Abstraction |
|-----------|------------|------------|-------------|
| **Auth Token** | `GITHUB_TOKEN` | `CI_JOB_TOKEN` / `GITLAB_TOKEN` | Auto-detected per platform |
| **Project ID** | `owner/repo` | Numeric ID or `namespace/project` | Passed as string |
| **Fetch MR/PR** | `repo.get_pull(number)` | `project.mergerequests.get(iid)` | `get_context()` |
| **Summary Comment** | `pr.create_issue_comment()` | `mr.notes.create()` | `post_summary_comment()` |
| **Inline Comments** | `pr.create_review_comment()` | `mr.discussions.create()` with position | `post_inline_comments()` |
| **Status Update** | `commit.create_status()` | `commit.statuses.create()` | `update_status()` |
| **State Values** | `success`, `failure`, `pending` | `success`, `failed`, `running` | Mapped internally |

## Code Reuse

Both platforms **share**:
- ✅ Language detection logic (LANGUAGE_EXTENSIONS)
- ✅ Dependency file detection (DEPENDENCY_FILES)
- ✅ Change type detection (security patterns, breaking changes, etc.)
- ✅ Comment formatting (AI-generated or simple templates)
- ✅ Summary generation
- ✅ All review aspects (Python, JS, AI reviews)
- ✅ Orchestration logic
- ✅ Configuration system

Only **platform-specific**:
- ❌ API client initialization
- ❌ HTTP request details
- ❌ Response parsing
- ❌ Inline comment positioning (GitHub: line number, GitLab: diff refs)

## Testing

All existing tests pass:

```bash
uv run pytest tests/ -v
# ============================== 18 passed ==============================
```

## Benefits of This Abstraction

1. **Clean Separation**: Platform logic isolated in `lib/platform/`
2. **Easy Extension**: Add new platforms by implementing `CodeReviewPlatform`
3. **No Code Duplication**: Shared logic in base classes
4. **Backwards Compatible**: Existing GitHub code still works
5. **Testable**: Mock platforms for unit tests
6. **Type Safe**: Abstract methods enforce contract

## Next Steps

To complete the GitLab integration:

1. **Create GitLab CI Templates** (separate GitLab wrapper project)
2. **Add Example Configs** (show users how to configure)
3. **Documentation** (GITLAB_INTEGRATION.md)
4. **Test on Real GitLab Project** (validate MR posting)

## Files Modified

### New Files
- `lib/platform/__init__.py` - Package exports
- `lib/platform/base.py` - Abstract interfaces
- `lib/platform/factory.py` - Platform detection and creation
- `lib/platform/github_platform.py` - GitHub implementation
- `lib/platform/gitlab_platform.py` - GitLab implementation

### Modified Files
- `main.py` - Uses platform abstraction, auto-detects platform
- `lib/orchestrator.py` - Added `run_review_pipeline_with_context()`
- `pyproject.toml` - Added `python-gitlab` dependency

### Unchanged Files
- `lib/pr_context.py` - Kept for backwards compatibility
- `lib/github_reporter.py` - Kept for backwards compatibility
- All analyzers, AI review, config, models - No changes needed!

## Example Usage

### GitHub Actions Workflow (Unchanged)

```yaml
name: AI Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run AI Review
        run: python main.py --repo ${{ github.repository }} --pr ${{ github.event.pull_request.number }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### GitLab CI (New!)

```yaml
ai-review:
  stage: review
  image: python:3.11
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    # Install dependencies
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.local/bin:$PATH"
    - curl -fsSL https://storage.googleapis.com/anthropic-files/claude-code/install.sh | bash

    # Clone review system from GitHub
    - git clone https://github.com/your-org/ai-review-cicd-actions.git /tmp/review
    - cd /tmp/review && uv sync

    # Run review (auto-detects GitLab)
    - |
      uv run python main.py \
        --repo "$CI_PROJECT_PATH" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --project-root "$CI_PROJECT_DIR"
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY  # From CI/CD settings
    # CI_JOB_TOKEN is automatically provided
```

## Summary

✅ **Clean abstraction layer implemented**
✅ **Both GitHub and GitLab supported**
✅ **All tests passing**
✅ **Zero code duplication**
✅ **Backwards compatible**
✅ **Ready for GitLab CI templates**

The codebase is now platform-agnostic while maintaining all existing functionality!
