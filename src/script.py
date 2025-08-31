import os
import re
import json
import subprocess
import argparse
from publishers import GitIssuePublisher, GitPRPublisher

def extract_message(text):
    pattern = r'\[C:START\](.*?)\[C:END\]'
    matcher = re.search(pattern, text, re.DOTALL)
    if matcher:
        raw_message = matcher.group(1).strip()
        cleaned_message = re.sub(r'^[^{]*|[^}]*$', '', raw_message)
        return cleaned_message
    return None

def get_diff(gh_before, sha):
    return subprocess.check_output(['git', 'diff', gh_before, sha, "--word-diff"]).decode('utf-8')

def review(openai_key, assistant_id, token, repo, branch, message, gh_before, sha, is_pr=False, pr_number=None):
    if is_pr and pr_number:
        git_publisher = GitPRPublisher(token, repo, branch, sha, pr_number)
    else:
        git_publisher = GitIssuePublisher(token, repo, branch, sha)

    try:
        diff = get_diff(gh_before, sha)
    except subprocess.CalledProcessError as e:
        print(f"Error generating git diff: {e}")
        return

    item = f'User-Suggested Message: {message}\n\nCommit Diff: {diff}'

    try:
        note = subprocess.check_output([
            'cururo', 
            '--item', item, 
            '--openai-key', openai_key, 
            '--assistant-id', assistant_id,
        ]).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error running cururo: {e}")
        return
    
    response = extract_message(note)
    if not response:
        print("No response extracted from the note.")
        return

    try:
        response = json.loads(response)
    except json.JSONDecodeError:
        print(f"Error decoding JSON response: {response}")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    try:
        if is_pr and pr_number:
            pr_num, comment_id = git_publisher.publish(response)
        else:
            issue_number, comment_id = git_publisher.publish(response)
        
        author = git_publisher.user
        print(f"Review completed for user: {author}")
    except Exception as e:
        print(f"Error publishing review: {e}")


        
def main():
    parser = argparse.ArgumentParser(description="Commit message and diff handler with OpenAI assistance.")

    parser.add_argument('--openai-key', default=os.getenv('OPENAI_API_KEY'), help='OpenAI API key')
    parser.add_argument('--assistant-id', default=os.getenv('OPENAI_ASSISTANT_ID'), help='OpenAI assistant ID')
    parser.add_argument('--token', default=os.getenv('GH_TOKEN'), help='GitHub token')

    parser.add_argument('--repo', default=os.getenv('REPO'), help='Repository name')
    parser.add_argument('--branch', default=os.getenv('BRANCH'), help='Branch of work')
    parser.add_argument('--gh-before', default=os.getenv('GH_BEFORE'), help='GitHub before SHA')
    parser.add_argument('--sha', default=os.getenv('SHA'), help='Commit SHA')
    parser.add_argument('--message', default=os.getenv('MESSAGE'), help='Commit message')

    parser.add_argument('--is-pr', action='store_true', help='Indicates if this is a pull request')
    parser.add_argument('--pr-number', type=int, help='Pull request number (required if --is-pr is set)')

    args = parser.parse_args()

    if args.is_pr and not args.pr_number:
        parser.error("--pr-number is required when --is-pr is set")

    review(args.openai_key, args.assistant_id, args.token, args.repo, args.branch, args.message, args.gh_before, args.sha, args.is_pr, args.pr_number)

if __name__ == "__main__":
    main()
