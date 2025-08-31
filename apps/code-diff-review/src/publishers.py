import re
from typing import Optional, Dict
from cururo.util.publisher import Publisher
from github import Github, Auth, GithubException

class MermaidPrivate:
    def __init__(self, pattern=r'```mermaid\n(.*?)\n```', types='journey'):
        self.pattern=pattern
        self.types=types

    def generate_journey(self, title, to_add:str, body=''):
        code, exists = self.get_mermaid_code(title, body)
        code = self.append2mermaid(code, to_add)
        return self.insert_code(body, code, exists)

    def journey(self, title):
        return f'journey\ntitle {title}'

    def insert_code(self, body: str, mermaid_code: str, replace=True) -> str:
        if replace:
            return re.sub(self.pattern, f'```mermaid\n{mermaid_code}\n```', body, flags=re.DOTALL)
        else:
            return body + f'\n```mermaid\n{mermaid_code}\n```'

    def get_mermaid_code(self, title: str, body: str):
        match = re.search(self.pattern, body, re.DOTALL)
        if match:
            return match.group(1), True
        return self.journey(title), False

    def dict2section(self, section: str, steps: Dict[str, str], who: str) -> str:
        section_str = f'section {section}\n'
        for step, value in steps.items():
            section_str += f'{step}: {value}: {who}\n'
        return section_str
    
    def append2mermaid(self, mermaid: str, data: str) -> str:
        return f'{mermaid}\n{data}'

class GitBasePublisher(Publisher):
    """
    Base class for GitHub publishers with common functionality.
    """

    def __init__(self, _api_key: str, repo_name: str, branch: str, sha: str):
        """
        Initializes the base publisher with authentication and common details.

        :param _api_key: The GitHub API key for authentication.
        :param repo_name: The name of the GitHub repository.
        :param branch: The name of the branch.
        :param sha: The commit SHA.
        """
        super().__init__()

        try:
            _auth = Auth.Token(_api_key)
            self.__github = Github(auth=_auth)
            self.repo = self.__github.get_repo(repo_name)
            self.branch = branch
            self.sha = sha

            commit = self.repo.get_commit(self.sha)
            self.user = commit.author.login
        except GithubException as e:
            raise Exception(f"Error initializing GitHub client: {e}")

    def generate_base_report(self, data):
        """
        Generates the base report structure common to both issues and PRs.
        
        :param data: The review data.
        :return: List of report lines.
        """
        report = [
            "### 📝 Message Analysis",
            "| **Metric** | **Value** | **Score** |",
            "|------------|-----------|-----------|",
            f"| **Provided Message** | `{data['message']['provided']}` | - |",
            f"| **Generated Message** | `{data['message']['generated']}` | - |",
            f"| **Adherence Score** | {data['message']['adherence']['comment']} | {data['message']['adherence']['score']} {data['message']['adherence']['emoji']} |",
            "",
            "### 🏗️ Code Quality",
            "| **Aspect** | **Score** | **Details** |",
            "|------------|-----------|-------------|",
            f"| **Complexity** | - | {data['codeComplexity']['comment']} |",
            f"| **Vulnerability** | {data['codeVulnerability']['score']} {data['codeVulnerability']['emoji']} | {data['codeVulnerability']['comment']} |",
            "",
            "### 🎯 SOLID Principles",
            "| **Principle** | **Score** | **Assessment** |",
            "|----------------|-----------|---------------|"
        ]

        for principle, details in data['codeSOLID'].items():
            principle_name = principle.replace('_', ' ').title()
            report.append(f"| {principle_name} | {details['score']} {details['emoji']} | {details['comment']} |")

        return report

class GitIssuePublisher(GitBasePublisher):
    """
    A class to publish and manage GitHub issues with branch-specific threading and graph updates.
    """

    def publish(self, data):
        """
        Publishes or updates an issue with the graph and body content.

        :param data: The body for the issue.
        :return: Tuple of (issue_number, comment_id)
        """
        try:
            title = f"Automated Issue on branch {self.branch}"
            existing_issue = self.get_thread(title)
            updated_body = self.generate_issue(existing_issue.body or '', 
                                                        message=data['message']['adherence']['score'],
                                                        vulnerability=data['codeVulnerability']['score'])
            existing_issue.edit(body=updated_body)
            comment = existing_issue.create_comment(self.generate_report(data))

            return existing_issue.number, comment.id
        except GithubException as e:
            raise Exception(f"Error publishing issue: {e}")
 
    def get_thread(self, title: str, body: Optional[str] = ''):
        """
        Searches for an issue by title and creates or reopens it if necessary.

        :param title: The title of the issue to search or create.
        :param body: The body text for a new issue.
        :return: The existing or newly created issue.
        """
        try:
            issues = self.repo.get_issues(state='all')
            existing_issue = next((issue for issue in issues if issue.title == title), None)

            if existing_issue:
                if existing_issue.state != 'open':
                    existing_issue.edit(state='open')
                existing_issue.add_to_assignees(self.user)
                return existing_issue

            new_issue = self.repo.create_issue(title=title, body=body, assignee=self.user)
            return new_issue

        except GithubException as e:
            raise Exception(f"Error threading issue: {e}")

    def generate_report(self, data):
        """
        Generates a report for issues with the old format for backward compatibility.
        """
        report = [
            f"## Commit Review Summary [{self.sha}]",
            "| **Author** | **Provided Message** | **Generated Message** | **Adherence Score** | **Comment** |",
            "|------------|----------------------|-----------------------|---------------------|-------------|",
            f"| @{self.user} | '{data['message']['provided']}' | '{data['message']['generated']}' | {data['message']['adherence']['score']} {data['message']['adherence']['emoji']} | *{data['message']['adherence']['comment']}* |",
            "\n### Code Complexity",
            "| **Complexity Comment** |",
            "|------------------------|",
            f"| {data['codeComplexity']['comment']} |",
            "\n### Code Vulnerability",
            "| **Score** | **Comment** |",
            "|-----------|-------------|",
            f"| {data['codeVulnerability']['score']} {data['codeVulnerability']['emoji']} | {data['codeVulnerability']['comment']} |",
            "\n### SOLID Principles",
            "| **Principle** | **Score** | **Comment** |",
            "|----------------|-----------|-------------|"
        ]

        for principle, details in data['codeSOLID'].items():
            principle_name = principle.replace('_', ' ').title()
            report.append(f"| {principle_name} | {details['score']} {details['emoji']} | {details['comment']} |")

        return '\n'.join(report)

    def generate_issue(self, existing_body: str, **scores) -> str:
        """
        Appends adherence data to the existing comment body using a Mermaid XY diagram.

        :param existing_body: The existing comment body.
        :param scores: Dictionary with score details.
        :return: The updated comment body.
        """
        mermaid = MermaidPrivate()
        data = mermaid.dict2section(self.sha, scores, self.user)
        return mermaid.generate_journey("Scores History", data, existing_body)
    
class GitPRPublisher(GitBasePublisher):
    """
    A class to publish comments on GitHub pull requests with code diff review information.
    """

    def __init__(self, _api_key: str, repo_name: str, branch: str, sha: str, pr_number: int):
        """
        Initializes the GitPRPublisher with authentication, repository, and PR details.

        :param _api_key: The GitHub API key for authentication.
        :param repo_name: The name of the GitHub repository.
        :param branch: The name of the branch related to the PR.
        :param sha: The commit SHA related to the PR.
        :param pr_number: The pull request number.
        """
        super().__init__(_api_key, repo_name, branch, sha)
        self.pr_number = pr_number

        try:
            self.pr = self.repo.get_pull(pr_number)
        except GithubException as e:
            raise Exception(f"Error getting pull request: {e}")

    def publish(self, data):
        """
        Publishes a comment on the pull request with the code diff review information.

        :param data: The review data to publish.
        :return: Tuple of (pr_number, comment_id)
        """
        try:
            comment_body = self.generate_report(data)
            comment = self.pr.create_issue_comment(comment_body)
            return self.pr_number, comment.id
        except GithubException as e:
            raise Exception(f"Error publishing PR comment: {e}")

    def generate_report(self, data):
        """
        Generates a formatted report for the PR comment.
        
        :param data: The review data.
        :return: Formatted markdown string for the comment.
        """
        report = [
            f"## 🔍 Code Diff Review Summary",
            f"**Commit:** `{self.sha[:8]}` | **Branch:** `{self.branch}`",
            ""
        ]
        
        report.extend(self.generate_base_report(data))
        
        report.extend([
            "",
            "---",
            f"*Review generated by AI for commit {self.sha[:8]} on branch `{self.branch}`*"
        ])

        return '\n'.join(report) 
    