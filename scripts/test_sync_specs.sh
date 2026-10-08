#!/usr/bin/env bash
# Self-check for sync-specs.sh with a fake docker (containers = local dirs). Never touches real containers.
# Usage: bash scripts/test_sync_specs.sh   (prints PASS/FAIL per case; exit 1 on any FAIL)
# shellcheck disable=SC2016,SC2034  # check() evals its single-quoted condition later
set -euo pipefail
SRC=$(realpath "$(dirname "$0")/../sync-specs.sh"); T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
export FAKE="$T/containers"; mkdir -p "$FAKE/frontend" "$FAKE/backend" "$T/bin"
cat > "$T/bin/docker" <<'SHIM'
#!/usr/bin/env bash
set -euo pipefail
up() { [[ -d $FAKE/$1 ]] || { echo "Error: No such container: $1" >&2; exit 1; }; }   # stopped = dir renamed away
map() { if [[ $1 == *:* ]]; then up "${1%%:*}"; echo "$FAKE/${1%%:*}${1#*:}"; else echo "$1"; fi; }
case $1 in
  cp) s=$(map "$2"); d=$(map "$3")
      if [[ $2 == - ]]; then [[ -d $d ]] || { echo "no such dir $3" >&2; exit 1; }; tar -x -C "$d"
      else [[ -e $s ]] || { echo "no such path $2" >&2; exit 1; }; cp -a "$s" "$d"; fi ;;
  exec) shift; [[ $1 == -i ]] && shift; c=$1; shift; up "$c"
        a=(); for x in "$@"; do [[ $x == /* ]] && x=$FAKE/$c$x; a+=("$x"); done; "${a[@]}" ;;
esac
SHIM
chmod +x "$T/bin/docker"; export PATH="$T/bin:$PATH"
R="$T/repo"; C="$FAKE/backend/workspaces/haisir-specs"
mkdir -p "$R"/{target,Implementation_planning,vision/requirements,vision/prototypes}; cd "$R"; git init -q
git config user.email t@t; git config user.name t
printf '1\n2\n3\n4\n5\n6\n7\n' > Implementation_planning/TASKS.md
echo a > target/a.md; echo b > target/b.md; echo d > target/d.md; echo e > target/e.md; echo c > CLAUDE.md; echo v > vision/requirements/v.md; echo p > vision/prototypes/p.html
cp "$SRC" sync-specs.sh; git add -A; git commit -qm init
run() { (cd /; "$R/sync-specs.sh" "$@") 2>&1 || true; }   # from another cwd on purpose
fail=0; check() { if eval "$2"; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

echo x >> target/a.md; out=$(run push backend)
check push-refuse-dirty '[[ $out == REFUSED* && ! -e $C ]]'; git checkout -q target/a.md

out=$(run push backend)
check push-refuse-no-marker '[[ $out == REFUSED*--force* && ! -e $C/.spec-sha ]]'
out=$(run push backend --force)
check push-marker '[[ $out == "OK pushed"* && $(cat $C/.spec-sha) == $(git rev-parse HEAD) && -f $C/vision/requirements/v.md && ! -e $C/vision/prototypes && -f $C/CLAUDE.md ]]'

sed -i 's/^2$/2 [x] done/' "$C/Implementation_planning/TASKS.md"; echo new > "$C/target/new.md"; echo cb >> "$C/target/b.md"; rm "$C/target/e.md"
sed -i 's/^6$/6 spec-ahead/' Implementation_planning/TASKS.md; git rm -q target/b.md target/d.md; git commit -qam host
out=$(run pull backend)
check pull-clean-merge '[[ $(head -1 <<<"$out") == "OK merged 1 clean 3 conflicts 0" ]] && grep -q "2 \[x\] done" Implementation_planning/TASKS.md && grep -q "6 spec-ahead" Implementation_planning/TASKS.md && grep -q "^MERGED Implementation_planning/TASKS.md (-1 lines)" <<<"$out" && grep -q "^CONTAINER-ONLY target/new.md" <<<"$out" && [[ ! -e target/new.md && ! -e target/b.md ]]'
# b.md changed in the container: reported; d.md untouched there: the host deletion stands silently
check pull-host-deleted '[[ $out == *"HOST-DELETED target/b.md"* && $out != *target/d.md* ]]'
check pull-container-deleted '[[ $out == *"CONTAINER-DELETED target/e.md"* && -f target/e.md ]]'
git commit -qam merged

echo late >> "$C/target/a.md"; out=$(run push backend)
check push-refuse-unpulled '[[ $out == REFUSED*"not pulled"* && $(tail -1 $C/target/a.md) == late && $(cat $C/.spec-sha) == $(git rev-list --max-parents=0 HEAD) ]]'
sed -i '$d' "$C/target/a.md"; out=$(run push backend)   # container back to what the last pull saw
check push-after-pull '[[ $out == "OK pushed"* && $(cat $C/.spec-sha) == $(git rev-parse HEAD) ]]'
check push-exact-copy '[[ ! -e $C/target/new.md && ! -e $C/target/b.md && ! -e $C/target/d.md && -f $C/target/e.md ]] && grep -q "2 \[x\] done" $C/Implementation_planning/TASKS.md'

sed -i 's/^4$/4 container/' "$C/Implementation_planning/TASKS.md"; sed -i 's/^4$/4 host/' Implementation_planning/TASKS.md; git commit -qam host2
out=$(run pull backend)
check pull-conflict '[[ $(head -1 <<<"$out") == "OK merged 0 clean 4 conflicts 1" ]] && grep -q "^CONFLICT Implementation_planning/TASKS.md (1)" <<<"$out" && grep -q "^<<<<<<< host" Implementation_planning/TASKS.md && grep -q "2 \[x\] done" Implementation_planning/TASKS.md'
git checkout -q .

echo dirty >> CLAUDE.md; before=$(cat Implementation_planning/TASKS.md); out=$(run pull backend)
check pull-refuse-dirty '[[ $out == REFUSED* && $(cat Implementation_planning/TASKS.md) == "$before" ]]'; git checkout -q .

rm "$C/.spec-sha"; out=$(run pull backend)
check pull-refuse-no-marker '[[ $out == REFUSED*--base* ]]'
out=$(run pull backend --base "$(git rev-list --max-parents=0 HEAD)")
check pull-legacy-base '[[ $out == "OK merged 0 clean 4 conflicts 1"* ]]'; git checkout -q .

printf '\x89PNG\0\1' > target/s.png; git add target/s.png; git commit -qm bin; run push backend --force >/dev/null
printf '\x89PNG\0\2' > "$C/target/s.png"; printf '\x89PNG\0\3' > target/s.png; git commit -qam bin2
out=$(run pull backend)
check pull-binary-skip '[[ $(head -1 <<<"$out") == "OK merged 0 clean 5 conflicts 0" ]] && grep -q "^BINARY target/s.png$" <<<"$out" && git diff --quiet'

mkdir -p "$T/bin2"; printf '#!/usr/bin/env bash\n[[ $1 == merge-file && $* == *target/a.md* ]] && exit 255\nexec %s "$@"\n' "$(command -v git)" > "$T/bin2/git"; chmod +x "$T/bin2/git"
sed -i 's/^1$/1 container/' "$C/Implementation_planning/TASKS.md"; echo zc >> "$C/target/a.md"
sed -i 's/^7$/7 host/' Implementation_planning/TASKS.md; git commit -qam host3
out=$(PATH="$T/bin2:$PATH" run pull backend)
check pull-no-partial-write '[[ $out == REFUSED*target/a.md* ]] && git diff --quiet'

out=$(run pull all); check pull-all-refused '[[ $out == *"exactly one"* ]]'

mv "$FAKE/backend" "$FAKE/backend.off"; git checkout -q .
out=$(run pull backend --base "$(git rev-parse HEAD)"); out2=$(run push backend --force)
check docker-down-refused '[[ $out == *"REFUSED cannot reach container backend"* && $out2 == *"REFUSED cannot reach container backend"* ]]'
mv "$FAKE/backend.off" "$FAKE/backend"

out=$(cd "$T" && bash repo/sync-specs.sh bogus 2>&1 || true)
check usage-relative-path '[[ $out == *"sync-specs.sh push"* ]]'
exit $fail
