#!/usr/bin/env bash
# Fetch a pull request's tree as data, for the checks that main runs.
#
# usage: fetch-candidate.sh <repository-url> <head> <accepted> <pull-number> [<directory>]
#
# <head> is the pull request's head commit and <accepted> the commit of main
# that the checks compare against; <pull-number> is the pull request whose
# refs/pull/<number>/head serves the head when the base repository does not
# serve its hash. <directory> (candidate by default) receives the head's tree,
# and <directory>.git is the fresh repository that holds it; neither may exist.
#
# The head is fetched by its commit hash, with a blob-less partial fetch, and
# main's commit with enough history to tell that it is an ancestor of the head:
# only then does a squash merge of the head put exactly its tree on main. The
# head's tree is listed from its objects and refused if it holds a symbolic
# link, a submodule or a .gitattributes file, before any of it is written; a
# tree that passes is written with a worktree checkout, which applies no
# attribute, filter or hook.
#
# Every Git command runs on the fresh repository or on the written tree, with
# the hooks path, the system and global configuration, the attribute file and
# the transport held to https, so that nothing in the tree is applied or run.
#
# No other text of the pull request is read, and nothing of the tree is
# exported: the checks of main take the paths they check as arguments.
set -euo pipefail

fail() {
  printf '%s\n' "$*" >&2
  exit 1
}

if (( $# < 4 || $# > 5 )); then
  fail "usage: $0 <repository-url> <head> <accepted> <pull-number> [<directory>]"
fi

repository_url=$1
head=$2
accepted=$3
pull_number=$4
directory=${5:-candidate}

# The workflow passes these values through the environment; require their shape
# here as well, so that no other text reaches a Git command or an argument.
if [[ ! "$head" =~ ^[0-9a-f]{40}$ ]]; then
  fail "the pull request's head is not a commit hash: $head"
fi
if [[ ! "$accepted" =~ ^[0-9a-f]{40}$ ]]; then
  fail "the accepted commit is not a commit hash: $accepted"
fi
if [[ ! "$pull_number" =~ ^[1-9][0-9]*$ ]]; then
  fail "the pull request's number is not a decimal number: $pull_number"
fi

case "$directory" in
  /*) candidate=$directory ;;
  *) candidate=$PWD/$directory ;;
esac
repository=$candidate.git

if [[ -e "$candidate" || -e "$repository" ]]; then
  fail "$candidate or $repository already exists"
fi
mkdir -p "$(dirname "$candidate")"

git_candidate() {
  GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_ATTR_NOSYSTEM=1 \
    git -c core.hooksPath=/dev/null \
      -c core.attributesFile=/dev/null \
      -c protocol.allow=never \
      -c protocol.https.allow=always \
      "$@"
}

git_candidate init --quiet --bare "$repository"
git_candidate -C "$repository" config remote.origin.url "$repository_url"
git_candidate -C "$repository" config remote.origin.promisor true
git_candidate -C "$repository" config remote.origin.partialclonefilter blob:none

# main's commit is served by the base repository itself; a head may come from a
# fork, which GitHub serves from the base repository by hash, or as the pull
# request's ref.
git_candidate -C "$repository" fetch --no-tags --filter=blob:none origin "$accepted"
if ! git_candidate -C "$repository" fetch --no-tags --filter=blob:none origin "$head"; then
  printf 'the base repository does not serve %s by hash; using refs/pull/%s/head\n' \
    "$head" "$pull_number" >&2
  git_candidate -C "$repository" fetch --no-tags --filter=blob:none origin \
    "refs/pull/$pull_number/head:refs/pull/$pull_number/head"
  served=$(git_candidate -C "$repository" rev-parse --verify "refs/pull/$pull_number/head^{commit}")
  if [[ "$served" != "$head" ]]; then
    fail "refs/pull/$pull_number/head is $served, not the head $head that the event names"
  fi
fi

# a head that does not contain main's commit would put more on main than its own
# tree when it merges, so the checks require it to be up to date with main
if ! git_candidate -C "$repository" merge-base --is-ancestor "$accepted" "$head"; then
  fail "the pull request is not up to date with main at $accepted; update it"
fi

# the list goes to a file first: a listing that fails part way must fail the
# fetch, not leave a truncated list that the loop would read as a whole tree
listing="$(mktemp)"
trap 'rm -f -- "$listing"' EXIT
git_candidate -C "$repository" ls-tree -r -z --full-tree "$head" > "$listing"

refused=0
while IFS= read -r -d '' entry; do
  metadata=${entry%%$'\t'*}
  if [[ "$metadata" == "$entry" ]]; then
    fail "the head's tree lists an entry without a path"
  fi
  path=${entry#*$'\t'}
  mode=${metadata%% *}
  if [[ "$mode" != 100644 && "$mode" != 100755 ]]; then
    printf 'refused a tree entry of mode %s: %q\n' "$mode" "$path" >&2
    refused=1
  elif [[ "$path" == .gitattributes || "$path" == */.gitattributes ]]; then
    printf 'refused a Git attribute file: %q\n' "$path" >&2
    refused=1
  fi
done < "$listing"
if (( refused != 0 )); then
  fail "the pull request's tree holds a symbolic link, a submodule or a .gitattributes file; the candidate was not written"
fi

git_candidate -C "$repository" worktree add --quiet --detach "$candidate" "$head"
tree=$(git_candidate -C "$repository" rev-parse --verify "$head^{tree}")
printf 'the candidate is the tree %s of the head %s, written to %s\n' \
  "$tree" "$head" "$candidate"
