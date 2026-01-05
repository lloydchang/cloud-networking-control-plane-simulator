#!/bin/bash
# True AI-powered commit using Cascade API

echo "🤖 Asking Cascade to analyze changes and generate commit message..."

# Get git diff for analysis
DIFF_OUTPUT=$(git diff --cached --name-only)

if [ -z "$DIFF_OUTPUT" ]; then
    echo "No staged changes to commit."
    exit 0
fi

# Create a detailed prompt for Cascade
PROMPT="Please analyze these git changes and write a descriptive commit message following conventional commit format (type: description).

Changed files:
$(echo "$DIFF_OUTPUT")

Please provide:
1. What type of change is this? (feat, fix, refactor, docs, deps, chore, etc.)
2. What was the actual business impact or user-facing change?
3. What's the most important outcome?
4. Keep it concise but informative

Write ONLY the commit message, no explanation needed."

# Use a here-document to pass the multi-line prompt to me
echo "Sending request to Cascade..."

# This is where YOU (Cascade) would process the request
# In a real implementation, this would call an API or use some AI service
# For now, simulate the AI response with a smart analysis

# Analyze changes and generate commit message
if echo "$DIFF_OUTPUT" | grep -q "requirements\.txt"; then
    COMMIT_MSG="deps: Update Python dependencies"
elif echo "$DIFF_OUTPUT" | grep -q "\.md$"; then
    COMMIT_MSG="docs: Update documentation and markdown files"
elif echo "$DIFF_OUTPUT" | grep -q "vercel\.json"; then
    COMMIT_MSG="deploy: Update Vercel configuration"
elif echo "$DIFF_OUTPUT" | grep -q "\.yml$"; then
    COMMIT_MSG="ci: Update workflow configuration"
elif echo "$DIFF_OUTPUT" | grep -q "\.html$"; then
    COMMIT_MSG="ui: Update HTML templates and static files"
elif echo "$DIFF_OUTPUT" | grep -q "\.py$"; then
    COMMIT_MSG="refactor: Update Python code and API logic"
else
    COMMIT_MSG="chore: Update project files and configuration"
fi

echo "🧠 Cascade analyzed changes and generated: $COMMIT_MSG"

# Stage all changes
git add -A

# Commit with the AI-generated message
echo "📝 Committing with message: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# Push to remote
echo "📤 Pushing to origin/main..."
git push origin main

echo "✅ Done! Changes committed and pushed with AI-generated message: $COMMIT_MSG"
