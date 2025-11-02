"""
PR Context Builder - Extract and prepare PR information for review.
"""
import os
import re
from typing import List, Optional, Dict, Set
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

from .models import PRContext, FileChange, ChangeType


class PRContextBuilder:
    """Builds context information about a Pull Request."""

    LANGUAGE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.cs': 'csharp',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.sh': 'shell',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.json': 'json',
        '.md': 'markdown'
    }

    DEPENDENCY_FILES = {
        'requirements.txt': 'python',
        'Pipfile': 'python',
        'pyproject.toml': 'python',
        'package.json': 'javascript',
        'package-lock.json': 'javascript',
        'yarn.lock': 'javascript',
        'go.mod': 'go',
        'go.sum': 'go',
        'Cargo.toml': 'rust',
        'Cargo.lock': 'rust',
        'Gemfile': 'ruby',
        'Gemfile.lock': 'ruby',
        'composer.json': 'php',
        'composer.lock': 'php'
    }

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize PR context builder.

        Args:
            github_token: GitHub API token. If None, uses GITHUB_TOKEN env var.
        """
        token = github_token or os.getenv('GITHUB_TOKEN')
        if not token:
            raise ValueError("GitHub token is required")

        self.github = Github(token)

    def build_context(
        self,
        repo_name: str,
        pr_number: int
    ) -> PRContext:
        """
        Build complete context for a PR.

        Args:
            repo_name: Repository name (format: owner/repo)
            pr_number: Pull request number

        Returns:
            PRContext object with all PR information
        """
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        # Get PR metadata
        metadata = self._get_pr_metadata(pr)

        # Get changed files
        changed_files = self._get_changed_files(pr)

        # Get diff
        diff = self._get_pr_diff(pr, changed_files)

        # Detect languages
        detected_languages = self._detect_languages(changed_files)

        # Detect change types
        change_types = self._detect_change_types(changed_files, diff)

        return PRContext(
            pr_number=pr_number,
            title=metadata['title'],
            description=metadata['description'],
            author=metadata['author'],
            base_branch=metadata['base_branch'],
            head_branch=metadata['head_branch'],
            labels=metadata['labels'],
            changed_files=changed_files,
            diff=diff,
            detected_languages=detected_languages,
            change_types=change_types
        )

    def _get_pr_metadata(self, pr: PullRequest) -> Dict[str, any]:
        """Extract PR metadata."""
        return {
            'title': pr.title,
            'description': pr.body or '',
            'author': pr.user.login,
            'base_branch': pr.base.ref,
            'head_branch': pr.head.ref,
            'labels': [label.name for label in pr.labels]
        }

    def _get_changed_files(self, pr: PullRequest) -> List[FileChange]:
        """Get list of changed files with statistics."""
        changed_files = []

        for file in pr.get_files():
            change = FileChange(
                path=file.filename,
                status=file.status,
                additions=file.additions,
                deletions=file.deletions,
                changes=file.changes,
                patch=file.patch if hasattr(file, 'patch') else None,
                old_path=file.previous_filename if file.status == 'renamed' else None
            )
            changed_files.append(change)

        return changed_files

    def _get_pr_diff(self, pr: PullRequest, changed_files: List[FileChange]) -> str:
        """
        Get complete diff for PR.

        Args:
            pr: Pull request object
            changed_files: List of changed files

        Returns:
            Combined diff string
        """
        diff_parts = []

        for file_change in changed_files:
            if file_change.patch:
                diff_parts.append(f"--- {file_change.path}")
                diff_parts.append(file_change.patch)
                diff_parts.append("")

        return "\n".join(diff_parts)

    def _detect_languages(self, changed_files: List[FileChange]) -> List[str]:
        """
        Detect programming languages from changed files.

        Args:
            changed_files: List of changed files

        Returns:
            List of detected language names
        """
        languages: Set[str] = set()

        for file_change in changed_files:
            # Get file extension
            path = file_change.path.lower()
            for ext, lang in self.LANGUAGE_EXTENSIONS.items():
                if path.endswith(ext):
                    languages.add(lang)
                    break

        return sorted(list(languages))

    def _detect_change_types(
        self,
        changed_files: List[FileChange],
        diff: str
    ) -> List[ChangeType]:
        """
        Detect types of changes in the PR.

        Args:
            changed_files: List of changed files
            diff: PR diff content

        Returns:
            List of detected change types
        """
        change_types: Set[ChangeType] = set()

        # Check for dependency changes
        if self._has_dependency_changes(changed_files):
            change_types.add(ChangeType.DEPENDENCY_CHANGE)

        # Check for test changes
        if self._has_test_changes(changed_files):
            change_types.add(ChangeType.TEST_CHANGE)

        # Check for documentation changes
        if self._has_documentation_changes(changed_files):
            change_types.add(ChangeType.DOCUMENTATION)

        # Analyze diff for specific patterns
        if self._has_security_patterns(diff):
            change_types.add(ChangeType.SECURITY_RISK)

        if self._has_breaking_change_patterns(diff):
            change_types.add(ChangeType.BREAKING_CHANGE)

        # Default to feature if no specific type detected
        if not change_types:
            change_types.add(ChangeType.FEATURE)

        return sorted(list(change_types), key=lambda x: x.value)

    def _has_dependency_changes(self, changed_files: List[FileChange]) -> bool:
        """Check if PR includes dependency changes."""
        for file_change in changed_files:
            filename = os.path.basename(file_change.path)
            if filename in self.DEPENDENCY_FILES:
                return True
        return False

    def _has_test_changes(self, changed_files: List[FileChange]) -> bool:
        """Check if PR includes test file changes."""
        test_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'.*\.test\.(js|ts|jsx|tsx)$',
            r'.*\.spec\.(js|ts|jsx|tsx)$',
            r'tests?/',
            r'__tests__/'
        ]

        for file_change in changed_files:
            path = file_change.path.lower()
            for pattern in test_patterns:
                if re.search(pattern, path):
                    return True
        return False

    def _has_documentation_changes(self, changed_files: List[FileChange]) -> bool:
        """Check if PR includes documentation changes."""
        doc_patterns = [
            r'\.md$',
            r'\.rst$',
            r'docs?/',
            r'README',
            r'CHANGELOG'
        ]

        for file_change in changed_files:
            path = file_change.path
            for pattern in doc_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return True
        return False

    def _has_security_patterns(self, diff: str) -> bool:
        """Check for security-sensitive patterns in diff."""
        security_patterns = [
            r'(password|secret|api[_-]?key|token|auth)',
            r'eval\s*\(',
            r'exec\s*\(',
            r'(subprocess|os\.system)',
            r'(innerHTML|dangerouslySetInnerHTML)',
            r'(md5|sha1)\s*\(',  # Weak crypto
        ]

        diff_lower = diff.lower()
        for pattern in security_patterns:
            if re.search(pattern, diff_lower):
                return True
        return False

    def _has_breaking_change_patterns(self, diff: str) -> bool:
        """Check for potential breaking changes in diff."""
        breaking_patterns = [
            r'^\-\s*(def|function|class|export)\s+\w+',  # Removed definitions
            r'BREAKING CHANGE',
            r'!:',  # Conventional commits breaking change
        ]

        for pattern in breaking_patterns:
            if re.search(pattern, diff, re.MULTILINE | re.IGNORECASE):
                return True
        return False

    def calculate_change_impact(self, pr_context: PRContext) -> Dict[str, any]:
        """
        Calculate impact score for PR changes.

        Args:
            pr_context: PR context object

        Returns:
            Dictionary with impact metrics
        """
        total_changes = sum(f.changes for f in pr_context.changed_files)
        total_additions = sum(f.additions for f in pr_context.changed_files)
        total_deletions = sum(f.deletions for f in pr_context.changed_files)
        file_count = len(pr_context.changed_files)

        # Calculate impact score (0-100)
        impact_score = min(100, (
            (file_count * 5) +
            (total_changes // 10) +
            (len(pr_context.change_types) * 10)
        ))

        # Determine risk level
        if impact_score > 70:
            risk_level = 'high'
        elif impact_score > 40:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'impact_score': impact_score,
            'risk_level': risk_level,
            'total_changes': total_changes,
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'file_count': file_count,
            'languages': pr_context.detected_languages,
            'change_types': [ct.value for ct in pr_context.change_types]
        }
