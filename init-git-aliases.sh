#!/bin/sh
# Git Aliases Init Script
# Works on macOS (bash/zsh) and Linux (bash/zsh/sh)
# Usage: source this file from your shell rc file, e.g.:
#   echo 'source /path/to/init-git-aliases.sh' >> ~/.bashrc
#   echo 'source /path/to/init-git-aliases.sh' >> ~/.zshrc

# ---------------------
# Status & Info
# ---------------------
alias gs='git status'
alias gss='git status -s'
alias gl='git log --oneline --graph --decorate'
alias gla='git log --oneline --graph --decorate --all'
alias glg='git log --stat'
alias gd='git diff'
alias gds='git diff --staged'
alias gdn='git diff --name-only'

# ---------------------
# Staging & Committing
# ---------------------
alias ga='git add'
alias gaa='git add --all'
alias gap='git add -p'
alias gc='git commit'
alias gcm='git commit -m'
alias gca='git commit --amend'
alias gcan='git commit --amend --no-edit'

# ---------------------
# Branching
# ---------------------
alias gb='git branch'
alias gba='git branch -a'
alias gbd='git branch -d'
alias gco='git checkout'
alias gcob='git checkout -b'
alias gsw='git switch'
alias gswc='git switch -c'

# ---------------------
# Push & Pull
# ---------------------
alias gp='git push'
alias gpf='git push --force-with-lease'
alias gpu='git push -u origin HEAD'
alias gpl='git pull'
alias gplr='git pull --rebase'
alias gf='git fetch'
alias gfa='git fetch --all --prune'

# ---------------------
# Rebase & Merge
# ---------------------
alias grb='git rebase'
alias grbc='git rebase --continue'
alias grba='git rebase --abort'
alias gm='git merge'
alias gma='git merge --abort'

# ---------------------
# Stash
# ---------------------
alias gst='git stash'
alias gstp='git stash pop'
alias gstl='git stash list'
alias gstd='git stash drop'
alias gsta='git stash apply'

# ---------------------
# Cherry-pick
# ---------------------
alias gcp='git cherry-pick'
alias gcpc='git cherry-pick --continue'
alias gcpa='git cherry-pick --abort'

# ---------------------
# Reset & Clean
# ---------------------
alias grh='git reset HEAD'
alias grh1='git reset HEAD~1'
alias grhh='git reset --hard HEAD'
alias gcl='git clean -fd'

# ---------------------
# Remote
# ---------------------
alias gr='git remote -v'
alias gra='git remote add'

# ---------------------
# Tags
# ---------------------
alias gt='git tag'
alias gtl='git tag -l'

# ---------------------
# Worktree
# ---------------------
alias gwt='git worktree'
alias gwtl='git worktree list'
alias gwta='git worktree add'
alias gwtr='git worktree remove'

# ---------------------
# Misc
# ---------------------
alias gbl='git blame'
alias gsh='git show'
alias gwip='git add --all && git commit -m "WIP"'

# Print loaded message
echo "Git aliases loaded. Run 'alias | grep git' to see all aliases."
