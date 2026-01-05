#!/bin/bash
# AI-powered commit using Cascade/Windsurf intelligence

echo "🤖 Asking Cascade to analyze changes and write commit message..."

# Get git diff for analysis
DIFF_OUTPUT=$(git diff --cached --name-only)

if [ -z "$DIFF_OUTPUT" ]; then
    echo "No staged changes to commit."
    exit 0
fi

# Create a prompt for Cascade to analyze changes
COMMIT_PROMPT="Please analyze these git changes and write a descriptive commit message following conventional commit format (type: description). 

Changed files:
$(echo "$DIFF_OUTPUT")

Focus on:
1. What was the actual business impact?
2. What type of change is this? (feat, fix, refactor, docs, deps, chore, etc.)
3. What's the most important user-facing impact?
4. Keep it concise but informative

Write just the commit message, no explanation needed."

# Ask Cascade to generate commit message
echo "$COMMIT_PROMPT" > /tmp/commit_request.txt
echo "📝 Prompt sent to Cascade. Please provide: commit message."

# Wait for Cascade to respond
echo "⏳ Waiting for Cascade to provide commit message..."
echo "💡 Once Cascade responds, I'll automatically execute the commit and push."
echo ""

# Read Cascade's response when user provides it
read -p "📝 Paste Cascade's commit message here: " COMMIT_MESSAGE

if [ -z "$COMMIT_MESSAGE" ]; then
    echo "⚠️ No commit message provided. Exiting."
    exit 1
fi

# Execute the commit with Cascade's message
echo "🚀 Executing: git commit -m \"$COMMIT_MESSAGE\""
git commit -m "$COMMIT_MESSAGE"

# Push to remote
echo "� Pushing to origin/main..."
git push origin main

echo "✅ Done! Changes committed and pushed with message: $COMMIT_MESSAGE"
