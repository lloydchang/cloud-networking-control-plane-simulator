#!/bin/bash
# Auto-commit and push all changes
echo "Auto-committing and pushing changes..."

# Add all changes
git add -A

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    # Commit with timestamp
    git commit -m "Auto-commit: $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Push to remote
    git push origin main
    
    echo "Changes committed and pushed successfully!"
fi
