# Git Helper Commands

This file contains common Git commands for managing the Smileys Blog repository.

## Basic Operations

### Check repository status
```bash
git status
```

### Add files to staging
```bash
# Add all changes
git add .

# Add specific file
git add filename.py

# Add specific directory
git add templates/
```

### Commit changes
```bash
# Commit with message
git commit -m "Your commit message here"

# Commit all tracked changes (skip staging)
git commit -am "Your commit message here"
```

### View commit history
```bash
# One line per commit
git log --oneline

# Detailed log
git log

# Show changes in commits
git log -p
```

## Branching

### Create and switch to new branch
```bash
# Create and switch to feature branch
git checkout -b feature/new-feature-name

# Or using newer syntax
git switch -c feature/new-feature-name
```

### Switch between branches
```bash
git checkout master
git checkout feature/new-feature-name

# Or using newer syntax
git switch master
git switch feature/new-feature-name
```

### List branches
```bash
git branch
```

### Merge branch
```bash
# Switch to master first
git checkout master

# Merge feature branch
git merge feature/new-feature-name
```

### Delete branch
```bash
# Delete merged branch
git branch -d feature/new-feature-name

# Force delete unmerged branch
git branch -D feature/new-feature-name
```

## Remote Repository (when you add one)

### Add remote repository
```bash
git remote add origin https://github.com/username/repository-name.git
```

### Push to remote
```bash
# Push master branch
git push origin master

# Push current branch
git push origin HEAD

# Set upstream and push
git push -u origin master
```

### Pull from remote
```bash
git pull origin master
```

### Clone repository
```bash
git clone https://github.com/username/repository-name.git
```

## Useful Commands

### Show differences
```bash
# Show unstaged changes
git diff

# Show staged changes
git diff --cached

# Show changes between commits
git diff HEAD~1 HEAD
```

### Undo changes
```bash
# Discard unstaged changes in file
git checkout -- filename.py

# Unstage file
git reset HEAD filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

### Stash changes
```bash
# Stash current changes
git stash

# Apply stashed changes
git stash pop

# List stashes
git stash list
```

## Recommended Workflow

1. **Before starting work:**
   ```bash
   git status
   git pull origin master  # if using remote
   ```

2. **Create feature branch:**
   ```bash
   git checkout -b feature/rss-improvements
   ```

3. **Make changes and commit frequently:**
   ```bash
   git add .
   git commit -m "Add RSS feed caching"
   ```

4. **When feature is complete:**
   ```bash
   git checkout master
   git merge feature/rss-improvements
   git branch -d feature/rss-improvements
   git push origin master  # if using remote
   ```

## Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Keep first line under 50 characters
- Add detailed description after blank line if needed
- Reference issues/tickets when applicable

### Examples:
```
Add RSS feed caching mechanism

- Implement Redis-based caching for feed generation
- Add cache invalidation on post updates
- Improve feed response time by 80%

Fixes #123
```

## Git Configuration

### Set up user information
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Useful aliases
```bash
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.unstage 'reset HEAD --'
```