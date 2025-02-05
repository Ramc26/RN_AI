import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

class GitHubRepoAnalyzer:
    def __init__(self, repo_url, branch_name):
        self.repo_url = repo_url
        self.branch = branch_name
        self.headers = {
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github+json"
        }
        self.owner, self.repo = self._parse_repo_url()
        print(f"Initialized GitHubRepoAnalyzer for repo: {self.repo_url} on branch: {self.branch}")

    def _parse_repo_url(self):
        path = urlparse(self.repo_url).path.strip("/")
        parts = path.split("/")
        return parts[0], parts[1]

    def get_commit_history(self, max_commits=10):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits"
        params = {
            "per_page": max_commits,
            "sha": self.branch
        }
        
        print(f"Fetching commit history from {url} with params: {params}")
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        commits = []
        for commit in response.json():
            commit_details = self._get_commit_details(commit['sha'])
            formatted_files = [f"{f['filename']} ({f['changes']} changes)" for f in commit_details['files']]
            commits.append({
                "sha": commit['sha'],
                "message": commit_details['commit']['message'],
                "author": commit_details['commit']['author']['name'],
                "date": commit_details['commit']['author']['date'],
                "files": formatted_files,
                "diff": self._get_commit_diff(commit['sha'])
            })
        
        print(f"Retrieved {len(commits)} commits.")
        return commits

    def _format_file_changes(self, files):
        return [{
            "filename": f['filename'],
            "status": f['status'],
            "additions": f['additions'],
            "deletions": f['deletions'],
            "changes": f['changes']
        } for f in files]

    def _get_commit_details(self, sha):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/{sha}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _get_commit_diff(self, sha):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/commits/{sha}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

def generate_release_notes(commits):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.2)
    
    prompt = f"""Analyze these GitHub commits from a specific branch and generate detailed release notes. 
    Focus on:
    - Code changes in diffs
    - File modification types (added/modified/deleted)
    - Commit message patterns
    - Impact analysis of changes

    Structure:
    1. Overview of changes
    2. Technical breakdown by category
    3. Notable code modifications
    4. Files changed summary

    Commits to analyze:
    {commits}
    
    Output in markdown with technical depth. Highlight significant code changes.
    """
    
    response = llm.invoke(prompt)
    return response.content

if __name__ == "__main__":
    # Load configuration from .env
    REPO_URL = os.getenv("REPO_URL")
    MAX_COMMITS = int(os.getenv("MAX_COMMITS", 2))
    BRANCH_NAME = os.getenv("BRANCH_NAME")
    
    if not all([REPO_URL, BRANCH_NAME]):
        raise ValueError("Missing required environment variables: REPO_URL, BRANCH_NAME")
    
    # Initialize analyzer with branch-specific configuration
    analyzer = GitHubRepoAnalyzer(repo_url=REPO_URL, branch_name=BRANCH_NAME)
    
    # Get commit history
    commits = analyzer.get_commit_history(max_commits=MAX_COMMITS)

    # Print commits in a readable format
    print("Commits:")
    for commit in commits:
        print(f"- SHA: {commit['sha']}")
        print(f"  Message: {commit['message']}")
        print(f"  Author: {commit['author']}")
        print(f"  Date: {commit['date']}")
        print(f"  Files Changed: {', '.join(commit['files'])}")
    
    # Generate release notes
    release_notes = generate_release_notes(commits)
    
    # Save and display results
    print(f"\nRelease Notes for {REPO_URL} (Branch: {BRANCH_NAME})")
    print(release_notes)
    
    with open("../release_notes.md", "w") as f:
        f.write(release_notes)
