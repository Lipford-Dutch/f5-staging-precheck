# Bash completion for check_multi
# Install:
#   source completions/check_multi.bash
# or copy to /etc/bash_completion.d/ (system) or ~/.local/share/bash-completion/completions/
#
# Completes options, check names (discovered from the installed lib/checks/),
# environment profiles, and file paths for the inventory argument.

_check_multi() {
  local cur prev words cword
  if declare -F _init_completion >/dev/null 2>&1; then
    _init_completion || return
  else
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
  fi

  local opts="-h --help -d --dry-run -v --verbose -t --threads \
    -o --output-dir -e --env -c --config -u --user -p --password \
    -y --yes --excel --no-color --list-checks --version"

  # Resolve the tool directory so we can discover checks/profiles dynamically.
  local bin_path root
  bin_path="$(command -v check_multi 2>/dev/null || echo "${COMP_WORDS[0]}")"
  root="$(cd "$(dirname "$(readlink -f "$bin_path" 2>/dev/null || echo "$bin_path")")/.." 2>/dev/null && pwd)"

  local checks="" envs=""
  if [[ -n "$root" && -d "$root/lib/checks" ]]; then
    checks="$(cd "$root/lib/checks" && for f in *.sh; do [[ -e $f ]] && printf '%s ' "${f%.sh}"; done)"
  fi
  if [[ -n "$root" && -d "$root/config/environments" ]]; then
    envs="$(cd "$root/config/environments" && for f in *.yaml; do [[ -e $f ]] && printf '%s ' "${f%.yaml}"; done)"
  fi

  case "$prev" in
    -e|--env)
      mapfile -t COMPREPLY < <(compgen -W "$envs" -- "$cur"); return ;;
    -t|--threads)
      mapfile -t COMPREPLY < <(compgen -W "4 8 12 16 20 32" -- "$cur"); return ;;
    -o|--output-dir|-c|--config)
      mapfile -t COMPREPLY < <(compgen -f -- "$cur"); return ;;
    -u|--user)
      mapfile -t COMPREPLY < <(compgen -u -- "$cur"); return ;;
  esac

  if [[ "$cur" == -* ]]; then
    mapfile -t COMPREPLY < <(compgen -W "$opts" -- "$cur")
    return
  fi

  # First non-option word is the check name; otherwise complete file paths.
  local i seen_check=0
  for ((i = 1; i < COMP_CWORD; i++)); do
    case "${COMP_WORDS[i]}" in
      -*) ;;
      *) seen_check=1; break ;;
    esac
  done

  if (( seen_check == 0 )); then
    mapfile -t COMPREPLY < <(compgen -W "$checks" -- "$cur")
  else
    mapfile -t COMPREPLY < <(compgen -f -- "$cur")
  fi
}

complete -F _check_multi check_multi
