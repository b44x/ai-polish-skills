#!/usr/bin/env bash
# ==============================================================================
# ai-polish-skills Installer
# Installs Polish AI skills into your AI assistant environment.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s inpost
#   curl -fsSL https://raw.githubusercontent.com/b44x/ai-polish-skills/main/install.sh | bash -s -- --global
# ==============================================================================

set -e

REPO_URL="https://github.com/b44x/ai-polish-skills"
TARBALL_URL="https://github.com/b44x/ai-polish-skills/archive/refs/heads/main.tar.gz"

# Colors
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${BLUE}║       ai-polish-skills • polskieskille.pl            ║${RESET}"
echo -e "${BOLD}${BLUE}║       Automatyczny instalator polskich skilli AI     ║${RESET}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════╝${RESET}\n"

# Defaults
TARGET_DIR=""
SELECTED_SKILLS=()
INSTALL_GLOBAL=false

# Check if first argument is a CLI subcommand
SUBCOMMAND=""
case "$1" in
  list|ls)
    SUBCOMMAND="list"
    shift
    ;;
  search|find)
    SUBCOMMAND="search"
    shift
    ;;
  info|show)
    SUBCOMMAND="info"
    shift
    ;;
  validate)
    SUBCOMMAND="validate"
    shift
    ;;
  update)
    SUBCOMMAND="update"
    shift
    ;;
  install)
    SUBCOMMAND="install"
    shift
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"

# If a management subcommand was requested and cli.py is available locally, delegate to it
if [[ -n "$SUBCOMMAND" && "$SUBCOMMAND" != "install" ]]; then
  if [[ -f "${SCRIPT_DIR}/scripts/cli.py" ]] && command -v python3 >/dev/null 2>&1; then
    exec python3 "${SCRIPT_DIR}/scripts/cli.py" "$SUBCOMMAND" "$@"
  fi
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --global|-g)
      INSTALL_GLOBAL=true
      shift
      ;;
    --antigravity|-a)
      TARGET_DIR=".agents/skills"
      shift
      ;;
    --claude|-c)
      TARGET_DIR=".claude/skills"
      shift
      ;;
    --dir|-d)
      TARGET_DIR="$2"
      shift 2
      ;;
    --help|-h)
      echo "Użycie: install.sh [polecenie] [opcje] [nazwa_skilla ...]"
      echo ""
      echo "Polecenia:"
      echo "  install [skille...]  Instaluje wskazane skille (domyślnie: wszystkie)"
      echo "  list                 Wyświetla listę dostępnych skilli"
      echo "  search <fraza>       Wyszukuje skille"
      echo "  info <skill>         Szczegółowe informacje o skillu"
      echo "  update               Aktualizuje zainstalowane skille"
      echo "  validate             Weryfikuje poprawność skilli"
      echo ""
      echo "Opcje instalacji:"
      echo "  --global, -g         Instalacja globalna dla Antigravity (~/.gemini/config/skills)"
      echo "  --antigravity, -a    Instalacja w lokalnym projekcie Antigravity (.agents/skills)"
      echo "  --claude, -c         Instalacja w lokalnym projekcie Claude Code (.claude/skills)"
      echo "  --dir, -d <katalog>  Instalacja we wskazanym katalogu docelowym"
      echo "  --help, -h           Pokaż pomoc"
      echo ""
      echo "Dostępne skille: inpost, biala-lista, filmweb, nbp, krs, imgw, sejm, nfz (domyślnie: wszystkie)"
      exit 0
      ;;
    *)
      SELECTED_SKILLS+=("$1")
      shift
      ;;
  esac
done

# Detect target directory if not set
if [[ -z "$TARGET_DIR" ]]; then
  if [[ "$INSTALL_GLOBAL" == true ]]; then
    TARGET_DIR="$HOME/.gemini/config/skills"
  elif [[ -d ".claude" ]]; then
    TARGET_DIR=".claude/skills"
  else
    # Default to .agents/skills (Antigravity, Cursor, Generic Agent)
    TARGET_DIR=".agents/skills"
  fi
fi

echo -e "${BOLD}1. Wykrywanie środowiska:${RESET}"
echo -e "   Katalog docelowy: ${GREEN}${TARGET_DIR}${RESET}"

# Create destination
mkdir -p "$TARGET_DIR"

# Determine source: local repo or remote download
TEMP_DIR=""
LOCAL_SKILLS_DIR=""

# Check if running from within the ai-polish-skills repository
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [[ -d "${SCRIPT_DIR}/skills" && -f "${SCRIPT_DIR}/scripts/validate_skills.py" ]]; then
  LOCAL_SKILLS_DIR="${SCRIPT_DIR}/skills"
  echo -e "   Źródło: ${BLUE}Lokalne repozytorium (${LOCAL_SKILLS_DIR})${RESET}"
else
  echo -e "   Źródło: ${BLUE}Pobieranie z GitHub (${REPO_URL})${RESET}"
  TEMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TEMP_DIR"' EXIT
  curl -fsSL "$TARBALL_URL" | tar -xz -C "$TEMP_DIR"
  LOCAL_SKILLS_DIR="$(echo "$TEMP_DIR"/ai-polish-skills-*/skills)"
fi

# Determine which skills to install
AVAILABLE_SKILLS=()
for d in "$LOCAL_SKILLS_DIR"/*/; do
  b="$(basename "$d")"
  if [[ "$b" != "_template" && "$b" != "." && "$b" != ".." ]]; then
    AVAILABLE_SKILLS+=("$b")
  fi
done

TO_INSTALL=()
if [[ ${#SELECTED_SKILLS[@]} -eq 0 ]]; then
  TO_INSTALL=("${AVAILABLE_SKILLS[@]}")
else
  for s in "${SELECTED_SKILLS[@]}"; do
    if [[ -d "$LOCAL_SKILLS_DIR/$s" ]]; then
      TO_INSTALL+=("$s")
    else
      echo -e "   ${YELLOW}Ostrzeżenie: Skill '$s' nie został znaleziony. Dostępne: ${AVAILABLE_SKILLS[*]}${RESET}"
    fi
  done
fi

if [[ ${#TO_INSTALL[@]} -eq 0 ]]; then
  echo -e "\n${RED}Błąd: Brak skilli do zainstalowania.${RESET}"
  exit 1
fi

echo -e "\n${BOLD}2. Instalacja skilli:${RESET}"
for skill in "${TO_INSTALL[@]}"; do
  src="$LOCAL_SKILLS_DIR/$skill"
  dest="$TARGET_DIR/$skill"

  rm -rf "$dest"
  cp -r "$src" "$dest"

  # Ensure scripts are executable
  if [[ -d "$dest/scripts" ]]; then
    chmod +x "$dest"/scripts/*.py 2>/dev/null || true
  fi

  echo -e "   ✓ Zainstalowano: ${GREEN}${skill}${RESET} ➔ ${dest}"
done

echo -e "\n${BOLD}${GREEN}✔ Gotowe!${RESET} Skille zostały poprawnie zainstalowane."
echo -e "Twój agent AI ma teraz dostęp do polskich usług i API.\n"
