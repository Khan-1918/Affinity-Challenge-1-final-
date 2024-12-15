import requests
import csv
import time
import os
from datetime import datetime, timedelta

# GitHub API Personal Access Token (replace or set as an environment variable)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "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")

# Validate GitHub Token
if not GITHUB_TOKEN or GITHUB_TOKEN == "your_personal_access_token_here":
    raise ValueError("GitHub Token is missing or invalid. Set it as an environment variable or update the script.")

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
DAYS_RANGE = 120  # Fetch data for the last 120 days
SINCE_DATE = (datetime.now() - timedelta(days=DAYS_RANGE)).strftime('%Y-%m-%d')  # Format as YYYY-MM-DD


# Check rate limits and wait if necessary
def check_rate_limit(response):
    remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
    reset_time = int(response.headers.get("X-RateLimit-Reset", time.time()))
    if remaining == 0:
        wait_time = reset_time - int(time.time())
        print(f"Rate limit reached. Waiting for {wait_time} seconds...")
        time.sleep(wait_time + 1)  # Wait a little longer to avoid immediate retries


# Function to fetch repositories with a specific query
def fetch_repositories(query, per_page=5, retries=3, timeout=10):
    repos = []
    page = 1
    url = f"https://api.github.com/search/repositories?q={query}+pushed:>{SINCE_DATE}&sort=stars&order=desc&per_page={per_page}"

    print(f"Debug: Query URL: {url}")  # Debugging query URL

    while True:
        try:
            response = requests.get(f"{url}&page={page}", headers=HEADERS, timeout=timeout)
            if response.status_code == 200:
                check_rate_limit(response)
                data = response.json()
                if 'items' in data and data['items']:
                    repos.extend(data['items'])
                    if len(data['items']) < per_page:
                        break  # No more results
                    page += 1
                else:
                    print("Debug: No repositories found in the response.")  # Debugging empty response
                    break
            elif response.status_code == 403:
                check_rate_limit(response)
            else:
                print(f"Error fetching repositories: {response.status_code} - {response.text}")
                break
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break

    return repos


# Function to fetch commit data including first and last commit details and commit count
def fetch_commit_data(owner, repo, retries=3, timeout=10):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    first_commit = {}
    last_commit = {}
    commits = []
    commit_count = 0
    params = {"since": SINCE_DATE, "per_page": 100}
    page = 1

    while True:
        try:
            response = requests.get(f"{url}?page={page}", headers=HEADERS, params=params, timeout=timeout)
            if response.status_code == 200:
                check_rate_limit(response)
                commit_data = response.json()
                if not commit_data:
                    break

                # Process commits
                for idx, commit in enumerate(commit_data):
                    author_name = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
                    timestamp = commit.get("commit", {}).get("author", {}).get("date")
                    if timestamp:
                        commit_time = datetime.fromisoformat(timestamp.replace("Z", ""))
                        committer_time_sec = int(commit_time.timestamp())

                        # Add commit details
                        commits.append({
                            "author": author_name,
                            "committer.time_sec": committer_time_sec
                        })

                        # Set first and last commit details
                        if not first_commit:
                            first_commit = {"author": author_name, "timestamp": timestamp}
                        last_commit = {"author": author_name, "timestamp": timestamp}

                commit_count += len(commit_data)
                page += 1
                if len(commit_data) < 100:  # Last page
                    break
            elif response.status_code == 403:
                check_rate_limit(response)
            else:
                print(f"Error fetching commits for {repo}: {response.status_code} - {response.text}")
                break
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching commits for {repo}: {e}")
            break

    return first_commit, last_commit, commits, commit_count


# Main function to fetch and save repository data
def main():
    query = "pandas"  # Change query as needed
    print(f"Fetching repositories updated in the last {DAYS_RANGE} days...")
    repos = fetch_repositories(query, per_page=5)

    if not repos:
        print("No repositories fetched. Try adjusting the query or increasing the date range.")
        return

    with open("github_repos_with_commit_data.csv", "w", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            "Repository",
            "Language",
            "Forks",
            "Author",
            "First Commit",
            "Last Commit",
            "Commit Count",
            "Commits",
            "committer.time_sec"
        ])

        for repo in repos:
            repo_name = repo['name']
            language = repo.get('language', "Not Specified")
            forks = repo.get('forks_count', 0)
            url = repo.get('html_url', "N/A")
            owner = repo['owner']['login']

            print(f"Fetching commit data for: {repo_name}...")
            first_commit, last_commit, commits, commit_count = fetch_commit_data(owner, repo_name)

            writer.writerow([
                repo_name,
                language,
                forks,
                first_commit.get("author", "Unknown"),
                first_commit.get("timestamp", "Unknown"),
                last_commit.get("timestamp", "Unknown"),
                commit_count,
                commits,
                commits[-1]["committer.time_sec"] if commits else "N/A"
            ])
            time.sleep(1)  # Avoid hitting the rate limit

    print("Data successfully saved to 'github_repos_with_commit_data5.csv'.")


if __name__ == "__main__":
    main()
