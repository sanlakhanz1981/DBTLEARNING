import os
import json
import snowflake.connector
from snowflake.snowpark import Session
from typing import Dict, List, Optional

# --- Configuration ---
# IMPORTANT: These should be set as environment variables in your CI/CD pipeline
# DO NOT hardcode sensitive credentials directly in your script.
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "YOUR_SNOWFLAKE_ACCOUNT_IDENTIFIER")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "YOUR_SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "YOUR_SNOWFLAKE_PASSWORD")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE", "YOUR_SNOWFLAKE_ROLE")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "YOUR_SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "YOUR_SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "YOUR_SNOWFLAKE_SCHEMA")

# Model to use for Cortex (ensure it's available in your Snowflake account)
CORTEX_MODEL = "mixtral-8x7b" # Or other models like 'llama3-8b', 'llama3-70b', 'mistral-large'

# --- Agent System Prompt ---
def get_system_prompt() -> str:
    """Defines the system prompt for the Cortex LLM."""
    return """You are an expert code optimization and generation agent. Your responsibilities include:

1. **Code Optimization**: Analyze provided code and suggest improvements for:
   - Performance optimization (Big O complexity, algorithm efficiency)
   - Memory efficiency and resource usage
   - Code readability and maintainability
   - Best practices adherence
   - Security improvements and vulnerability fixes
   - Error handling and edge cases
   - Design patterns implementation

2. **Code Generation**: Generate high-quality, production-ready code based on user requirements:
   - Follow language-specific best practices and conventions
   - Include proper error handling and validation
   - Add meaningful comments and documentation
   - Use efficient algorithms and appropriate data structures
   - Consider scalability and maintainability

3. **Code Review**: Provide detailed explanations including:
   - What changes were made and why
   - Performance implications and trade-offs
   - Alternative approaches and their pros/cons
   - Security considerations
   - Testing recommendations

Always provide complete, working code with clear explanations. Format code using proper markdown code blocks with language specification. Be specific about improvements and provide measurable benefits when possible."""

# --- Snowflake Connection and Cortex Interaction ---
def get_snowflake_session() -> Session:
    """Establishes a Snowflake Snowpark session."""
    connection_parameters = {
        "account": SNOWFLAKE_ACCOUNT,
        "user": SNOWFLAKE_USER,
        "password": SNOWFLAKE_PASSWORD,
        "role": SNOWFLAKE_ROLE,
        "warehouse": SNOWFLAKE_WAREHOUSE,
        "database": SNOWFLAKE_DATABASE,
        "schema": SNOWFLAKE_SCHEMA
    }
    # Using snowflake.connector directly for simpler query execution
    # In a real scenario, you might use snowpark session.sql() for more complex operations
    conn = snowflake.connector.connect(**connection_parameters)
    return Session(conn)

def analyze_code_with_cortex(session: Session, code_content: str, file_path: str = "unknown_file.py") -> str:
    """
    Sends code content to Snowflake Cortex for analysis and returns the response.
    
    Args:
        session: The active Snowflake Snowpark session.
        code_content: The actual code string to be analyzed.
        file_path: The path of the file being analyzed, for context.

    Returns:
        The analysis response from Snowflake Cortex.
    """
    print(f"Analyzing code from: {file_path} with model: {CORTEX_MODEL}")

    # Construct the full prompt for Cortex
    user_prompt = (
        f"Please perform a comprehensive code review and suggest optimizations for the following {os.path.basename(file_path).split('.')[-1].upper()} code. "
        f"Focus on performance, readability, security, and best practices. "
        f"Provide the optimized code in a markdown block, followed by a detailed explanation of changes.\n\n"
        f"Code from file '{file_path}':\n```\n{code_content}\n```"
    )
    full_cortex_prompt = f"{get_system_prompt()}\n\nUser Request: {user_prompt}"

    try:
        # Escape single quotes in the prompt for SQL
        escaped_prompt = full_cortex_prompt.replace("'", "''")
        
        # Call SNOWFLAKE.CORTEX.COMPLETE function
        # Using session.sql() for direct SQL execution
        df = session.sql(f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{CORTEX_MODEL}',
                '{escaped_prompt}'
            ) as RESPONSE;
        """).collect() # collect() fetches the results

        if df and len(df) > 0:
            response = df[0]["RESPONSE"]
            print(f"Cortex analysis successful for {file_path}.")
            return response
        else:
            print(f"No response received from Cortex for {file_path}.")
            return "Error: No response received from Cortex."

    except Exception as e:
        print(f"Error during Cortex analysis for {file_path}: {e}")
        return f"Error using Snowflake Cortex: {str(e)}\n" \
               "Please ensure:\n1. You have USAGE privileges on CORTEX functions\n" \
               "2. The selected model is available in your account\n" \
               "3. Your Snowflake role has proper permissions and network access."

# --- Code Reading and Filtering ---
def get_files_to_analyze(repo_path: str, file_extensions: List[str]) -> List[str]:
    """
    Recursively finds files with specified extensions in the given repository path.
    
    Args:
        repo_path: The root path of the cloned repository.
        file_extensions: A list of file extensions to include (e.g., ['.py', '.sql']).
    
    Returns:
        A list of absolute paths to files that should be analyzed.
    """
    files_to_analyze = []
    print(f"Scanning directory: {repo_path} for files with extensions: {file_extensions}")
    for root, _, files in os.walk(repo_path):
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                full_path = os.path.join(root, file)
                # Exclude common non-code files or build artifacts
                if not any(exclude_dir in full_path for exclude_dir in ['/.git/', '/node_modules/', '/__pycache__/', '/.venv/']):
                    files_to_analyze.append(full_path)
    print(f"Found {len(files_to_analyze)} files to analyze.")
    return files_to_analyze

def read_code_file(file_path: str) -> Optional[str]:
    """Reads the content of a code file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

# --- Main Execution Logic ---
def main():
    # In a CI/CD environment, the repository would already be cloned
    # We'll use a placeholder for the repository path.
    # For a real pipeline, this would be the current working directory or a specific checkout path.
    REPO_ROOT_PATH = os.getcwd() # Assumes the script runs from the root of the cloned repo

    # Define the file extensions you want to analyze
    # Customize this list based on your project's languages
    FILE_EXTENSIONS_TO_ANALYZE = [
        '.py', '.sql', '.js', '.ts', '.java', '.cpp', '.cs', '.go', '.rs', '.php',
        '.rb', '.swift', '.kt', '.dart', '.sh'
    ]

    print("Starting code analysis workflow...")

    # Step 1: Get files to analyze
    code_files = get_files_to_analyze(REPO_ROOT_PATH, FILE_EXTENSIONS_TO_ANALYZE)
    if not code_files:
        print("No code files found matching the specified extensions. Exiting.")
        return

    # Step 2: Establish Snowflake connection
    session = None
    try:
        session = get_snowflake_session()
        print("Successfully connected to Snowflake.")
    except Exception as e:
        print(f"Failed to connect to Snowflake: {e}")
        print("Please check your Snowflake connection parameters and permissions.")
        return

    # Store all analysis reports
    all_analysis_reports = []

    # Step 3: Iterate through files, analyze with Cortex
    for file_path in code_files:
        print(f"\nProcessing file: {file_path}")
        code_content = read_code_file(file_path)
        if code_content:
            report = analyze_code_with_cortex(session, code_content, file_path)
            if report:
                all_analysis_reports.append({
                    "file": os.path.relpath(file_path, REPO_ROOT_PATH), # Relative path for reporting
                    "analysis": report
                })
            else:
                print(f"Skipping empty or failed analysis for {file_path}.")
        else:
            print(f"Could not read content for file: {file_path}. Skipping.")

    # Step 4: Process and post feedback (conceptual)
    print("\n--- Code Analysis Summary ---")
    if all_analysis_reports:
        full_summary_report = "### Automated Code Review by Snowflake Cortex\n\n"
        for item in all_analysis_reports:
            full_summary_report += f"#### File: `{item['file']}`\n\n"
            full_summary_report += f"{item['analysis']}\n\n---\n\n"
        
        print(full_summary_report) # Print to console/CI/CD logs

        # --- Conceptual: Post to GitHub/Bitbucket API ---
        # This part requires specific API calls, authentication tokens, and target
        # (e.g., pull request ID, commit SHA).
        # You would use libraries like 'requests' to make HTTP POST/PUT requests
        # to the GitHub/Bitbucket API.

        # Example for GitHub (conceptual):
        # GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        # REPO_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER")
        # REPO_NAME = os.getenv("GITHUB_REPOSITORY").split('/')[-1]
        # PR_NUMBER = os.getenv("GITHUB_PR_NUMBER") # If triggered by PR
        # COMMIT_SHA = os.getenv("GITHUB_SHA") # If triggered by push

        # if GITHUB_TOKEN and PR_NUMBER:
        #     comment_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{PR_NUMBER}/comments"
        #     headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        #     payload = {"body": full_summary_report}
        #     # import requests
        #     # response = requests.post(comment_url, headers=headers, json=payload)
        #     # if response.status_code == 201:
        #     #     print("Successfully posted comment to GitHub PR.")
        #     # else:
        #     #     print(f"Failed to post comment to GitHub PR: {response.status_code} - {response.text}")
        # elif GITHUB_TOKEN and COMMIT_SHA:
        #     # Set a commit status
        #     status_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/statuses/{COMMIT_SHA}"
        #     headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        #     payload = {
        #         "state": "success", # or "failure", "error"
        #         "description": "Snowflake Cortex code analysis complete.",
        #         "context": "ci/snowflake-cortex-code-analysis",
        #         # "target_url": "Link to detailed report if available"
        #     }
        #     # import requests
        #     # response = requests.post(status_url, headers=headers, json=payload)
        #     # if response.status_code == 201:
        #     #     print("Successfully updated GitHub commit status.")
        #     # else:
        #     #     print(f"Failed to update GitHub commit status: {response.status_code} - {response.text}")
        # else:
        #     print("GitHub/Bitbucket API integration not configured or skipped.")

    else:
        print("No analysis reports generated.")

    # Close the Snowflake session
    if session:
        session.close()
        print("Snowflake session closed.")
    print("Code analysis workflow finished.")

if __name__ == "__main__":
    main()
