#!/bin/bash
# Smart commit with AI-style descriptive messages

# Get git status to understand what changed
CHANGES=$(git status --porcelain)

# Generate intelligent commit message based on changes
if echo "$CHANGES" | grep -q "requirements\.txt"; then
    MESSAGE="deps: Update Python dependencies"
elif echo "$CHANGES" | grep -q "\.md$"; then
    MESSAGE="docs: Update documentation and markdown files"
elif echo "$CHANGES" | grep -q "vercel\.json"; then
    MESSAGE="deploy: Update Vercel configuration"
elif echo "$CHANGES" | grep -q "\.yml$"; then
    MESSAGE="ci: Update workflow configuration"
elif echo "$CHANGES" | grep -q "\.html$"; then
    MESSAGE="ui: Update HTML templates and static files"
elif echo "$CHANGES" | grep -q "\.py$"; then
    MESSAGE="refactor: Update Python code and API logic"
else
    MESSAGE="chore: Update project files and configuration"
fi

# Add all changes
git add -A

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    # Commit with intelligent message
    git commit -m "$MESSAGE"
    
    # Push to remote
    git push origin main
    
    echo "✅ Committed and pushed: $MESSAGE"
fi
