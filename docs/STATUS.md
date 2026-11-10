# STATUS (Cline: read at the start of every task, update at the end)

## Current stage
Stage 13 IMPLEMENTED (act mode; branch fix/ir-loudness-and-onset): IR loudness
calibration & onset latency fix. Resolved the severe volume loss (estimated
20–30+ dB drop) and student WaveNet high-frequency collapse observed when adding
an IR to a slot. Root causes: (1) `ir.py:load_ir` used an overly sensitive
forward threshold (1e-4) that triggered on sample 1 from DC pre-ringing, leaving
105–174 samples (~2.5–4 ms) of dead-air latency that caused WaveNet phase cancellation
and an 8–18 dB midrange/high collapse; (2) `ir.py:bake` lacked perceptual loudness
matching, allowing cab bandpass filtering to drop mid/high energy.
Fixed: (1) `load_ir()` now trims silence right up to the first acoustic wavefront
spike (threshold `0.15 * peak` backed up by 4 samples), placing the impulse
within 4–10 samples of index 0; (2) `bake()` matches ITU-R BS.1770 K-weighted
loudness (_k_rms) between pre-IR and post-IR audio, with `fit_teacher_level()`
retained as a safety peak ceiling at 0.95; (3) `adapt.py` bumped to
`IR_PIPELINE_VERSION = "teacher-student-ir-v4"` to invalidate stale quiet cache
entries; (4) `tests/test_ir.py` updated with tests for wavefront onset trimming
and K-weighted loudness matching. Verified: test_ir.py passes (7/7).

## Stages
- 00 Windows survey: DONE (docs/plans/00-windows-survey.md, verified v1.2.3)
- 01 Avalonia/core Linux-readiness check: DONE (docs/plans/01-avalonia-linux-readiness.md)
- 02 Linux setup script: setup-linux.sh created + syntax-checked in sandbox; verified
  complete on host (venv pythons, uv CPythons 3.12.15/3.13.16, core_render built)
- 03 cl6x/bank.py portability: cl6x installed on host; bank.py:176 uses executable("cl6x");
  end-to-end bank build verified on host (stage 04). Committed as c5e554d.
- 04 .nam→bank + OpenFolder fix: DONE. OpenFolder fix committed (xdg-open on Linux,
  MainWindow.cs:278–281). A real .nam trained on CPU (10 epochs, ~5.5 min, ESR 0.074,
  correlation 0.964, review-quality run) and a bank built on the host at
  ~/nam-test/bank1/build/N2ZBANK.ZD2 and .ZIC. 100-epoch training and bank
  install verified on the MS-60B+ (fw 1.20) — the bank saves in a patch and
  survives a reboot (owner-verified, stage 10).
- 05 USB-MIDI install: DONE. MS-60B+ fw 1.20 seen by ALSA and python-rtmidi; PORT_MARKERS match needed no code change; msplus.py backup saved to ~/nam-test/pedal-backup-1; 10-epoch bank installed with nam2zoom install-bank (exit 0, readback hashes matched); effect shows up on the pedal, can be added to a patch, sounds approximately like the trained amp. GUI install and uninstall-bank verified in stage 06b; 100-epoch bank install verified on the MS-60B+ (fw 1.20) in stage 10.
- 05 step 1 (read-only code review): DONE, no code change needed for port matching; pedal seen by ALSA and Python, probe OK (MS-60B+ fw 1.20), full backup at ~/nam-test/pedal-backup-1.
- 05 step 2 (install command worked out, NOT run): DONE
- 06a smoke-test on Linux: DONE (docs/plans/06a-smoke-test-linux.md). Root cause:
  the smoke test ran only `paths.Python` (stomphacks venv, no nam/torch) while a
  source checkout has two venvs; fixed per Option A by splitting the import check
  across the two interpreters, portable branch byte-for-byte unchanged.
  Committed; host build and both smoke tests (--smoke-test, --gui-smoke-test)
  pass.
- 06b GUI install flow on host: DONE. Avalonia GUI verified on host with MS-60B+
  fw 1.20; uninstall bank and Build & install both worked. Verified: a 3-model
  bank with IRs, 10 training epochs each; GUI build and install, readback
  verified, each slot sounds distinct, effect saves in a patch and survives a
  reboot. Uninstall and install refuse to run while the pedal is on a patch that
  uses the N2Z effect (non-stock effect ID check); select a stock patch first.
- 06c Linux docs: DONE. Created docs/LINUX.md (prerequisites, setup-linux.sh,
  smoke tests, first use, stock-patch rule; facts from STATUS/plans, unverified
  items marked) and added a short Linux section to README.md linking it. GUI
  footer text left unchanged (no code change in this task).
- 09 GUI footer text for Linux: DONE (docs/plans/09-footer-text.md).
  StudioLayout.cs:315 branches on OperatingSystem.IsLinux(); Linux shows the
  USB-MIDI verified note; Windows/macOS text unchanged byte-for-byte.
- 10 Final v1 review and doc fixes: DONE. Diff review against upstream conventions passed (docs/plans/10-final-review.md); docs LINUX.md/STATUS.md updated for verified 100-epoch training and footer text.
- 11 Clearer cl6x install instructions + LINUX.md tidy: DONE. Reworded the cl6x Fix message in dev-setup-linux.sh and the cl6x section of docs/LINUX.md with the TI download link, full unattended install command (chmod +x, --mode unattended, --prefix), per-part explanation, no-PATH/no-restart note, one-line check, and "no source files" note. Added per-window PATH note and ~/.bashrc lines for dotnet and uv in both documents. Moved 100-epoch training and GUI footer from "What does not work" to "What works"; Other pedals stays. No logic or behaviour changes.
- 13 IR loudness & onset latency fix: DONE on branch fix/ir-loudness-and-onset. Trims leading silence to acoustic wavefront (0.15 * peak - 4 samples) in ir.py, matches ITU-R BS.1770 K-weighted loudness in bake(), bumps adapt.py to teacher-student-ir-v4, and adds comprehensive tests in tests/test_ir.py (7/7 pass).

## Environment
Host terminal (user runs these; Cline cannot see them):
- git, python3, cmake, gcc, g++, clang, ninja, flatpak: paths = <fill from `command -v` output>
- uv: ~/.local/bin/uv
- dotnet: ~/.dotnet/dotnet (.NET 10 SDK, installed with dotnet-install.sh)
- libasound2t64 + alsa-utils installed; kernel snd_seq loaded
- 32-bit libs (gcc-multilib, g++-multilib): installed if the optional step passed <confirm>
- cl6x (TI C6000 CGT 8.3.1): installed on host at .tooling/cgt-8.3.1/ti-cgt-c6000_8.3.1
  (unattended installer: --mode unattended --prefix; installer is 32-bit, bin/cl6x is a 64-bit
  static Linux program, --silicon_version=6740). Archive: https://software-dl.ti.com/codegen/non-esd/downloads/download_archive.htm
Cline sandbox (Flatpak):
- Has: git, python3, cmake, gcc, g++, ninja
- Missing: clang, dotnet, uv. Do not try to install them.

## Rules in force
- Branch: linux-port (base v1.2.3, 5bb02a2).
- v1: CPU-only training, Compact only.
- No sudo, no system installs, no new dependencies without owner approval.

## Done log
- 00 survey written and spot-checked (compact.py L22, TrainingRuntime.cs L13).
- 01 Avalonia/core readiness report: net10.0 both projects; only Linux code gap is
  OpenFolder (MainWindow.cs:279, explorer.exe); Python/MIDI paths already branch to
  Linux; blockers are cl6x.exe (bank.py:176) and missing Linux setup.
- 02 setup-linux.sh written and `bash -n` checked in sandbox. Mirrors setup.ps1 for the
  Linux CPU-only Compact path: pinned checkouts (stomp/nam/core/zoom-zt2), uv venvs
  (.tooling/stomphacks/.venv on STOMP_PYTHON default 3.13, .tooling/nam-train-venv on
  3.12), release/backend-requirements.txt pins + stomphacks requirements.txt,
  torch==2.11.0 from the CPU wheel index, -e neural-amp-modeler + soundfile==0.14.0,
  core_render via gcc/g++ + ninja into reference/nam_a2/build-core-ninja.
  No cl6x, no CUDA, no dotnet steps, no sudo.
- 03 cl6x portability: TI CGT 8.3.1 installed on host to .tooling/cgt-8.3.1 with the unattended
  installer (--mode unattended --prefix); installer is 32-bit but bin/cl6x is a 64-bit static
  Linux program. bank.py:14 now imports executable from platforms.py and bank.py:176 uses
  TOOLCHAIN / "bin" / executable("cl6x"), so Windows still resolves cl6x.exe. Nothing else in
  bank.py changed. End-to-end bank build verified on host (stage 04). Committed as c5e554d.
- 04 plan + OpenFolder fix (docs/plans/04-nam-to-bank.md): pipeline mapped (MainWindow.Add
  MainWindow.cs:152 → BankService.BuildAsync BankService.cs:118 → adapt under nam-train-venv →
  build-bank under stomphacks venv → N2ZBANK.ZD2/.ZIC bank.py:185). CPU path confirmed:
  adapt.py:248–251 accelerator auto→CPU without CUDA, learning.json's "gpu" default overwritten
  (adapt.py:249), torch installed CPU-only (setup-linux.sh:156); CUDA UI/runtime Windows-gated
  (MainWindow.cs:221, StudioLayout.cs:272, TrainingRuntime.cs:13). OpenFolder three-way branch
  applied; grep over apps/ found no other explorer.exe/Process.Start shell-out in the Avalonia
  app (BackendService.cs:51 launches backend Python only; nam2zoom-desktop is WinForms, untouched).
  Stage 04 host run done: OpenFolder fix committed (xdg-open on Linux); a real .nam trained
  on CPU (10 epochs, ~5.5 min, ESR 0.074, correlation 0.964, review-quality run); bank built
  on the host at ~/nam-test/bank1/build/N2ZBANK.ZD2 and .ZIC. (Correction: the
  claimed 100-epoch run ~/nam-test/bank100 was never started; no 100-epoch bank
  exists; 100-epoch training has NOT been run or tested on Linux.)
- 06a (docs/plans/06a-smoke-test-linux.md): four investigation answers written
  (smoke test picked `.tooling/stomphacks/.venv/bin/python3` via AppPaths.cs:24-27
  because setup-linux.sh creates no runtime/portable.marker; GUI actions split
  BankService.cs:80 adapt->nam-train-venv vs build/install->stomphacks venv;
  single-interpreter check valid only in portable bundles, per
  verify_portable.py:130). Owner-approved Option A applied: Program.cs keeps the
  original single command byte-for-byte when runtime/portable.marker exists,
  otherwise checks paths.Python (mido, rtmidi, construct, nam2zoom.template) then
  paths.Trainer (nam.cli, torch, numpy, scipy, soundfile), RequireSuccess() each.
  Verified by read-back and `git diff apps/`; committed; host build and both
  smoke tests pass.
- 06b GUI verified on host (owner): Avalonia GUI on Linux with MS-60B+ fw 1.20;
  uninstall bank and Build & install worked. Verified: a 3-model bank with IRs,
  10 training epochs each; GUI build and install, readback verified, each slot
  sounds distinct, effect saves in a patch and survives a reboot. Uninstall and
  install refuse to run while the pedal is on a patch that uses the N2Z effect
  (non-stock effect ID check); select a stock patch first.
- 06c Linux docs: created docs/LINUX.md (what works / what does not,
  prerequisites incl. TI cl6x installed by hand, setup-linux.sh +
  STOMP_PYTHON=3.12, build and the two smoke tests, first use, stock-patch rule;
  100-epoch training marked unverified) and inserted a short `## Linux` README
  section linking it. No code; GUI footer macOS text untouched (deferred).
- 06d docs/LINUX.md fixes: TI download link corrected (missing `downloads/`
  segment); cl6x location documented exactly as the code requires it
  (bank.py:21 `TOOLCHAIN = ROOT / ".tooling" / "cgt-8.3.1" /
  "ti-cgt-c6000_8.3.1"`, bank.py:176 `bin/cl6x`; setup-linux.sh neither
  installs nor searches for it) with the unattended `--prefix` command;
  First use rewritten to the real GUI (automatic header pedal check, Add
  NAMs/drop area, Pedal label, Choose IR..., Training epochs, Compact, Build
  effect / Build & install... / Uninstall bank..., approval dialogs showing
  the ZD2/ZIC SHA-256, Full backup before pedal changes); dotnet full-path
  hint added; setup-linux.sh confirmed executable so `./setup-linux.sh` kept.
  TI installer filename and the rest of the installer command line are marked
  unverified in the guide.
- 07b docs/LINUX.md fixes from the stage-07 clean-account walkthrough (stage 07
  passed and found these gaps): (1) uv install step (install script,
  ~/.local/bin, PATH note) added before setup-linux.sh; (2) .NET 10 SDK install
  step (dotnet-install.sh --channel 10.0, ~/.dotnet, PATH + DOTNET_ROOT notes);
  (3) cl6x TI download link and unattended --prefix command marked verified on a
  clean account, install location kept exactly as the code requires (bank.py:21
  TOOLCHAIN, bank.py:176 bin/cl6x); (4) audio-group prerequisite added
  (/dev/snd/seq is group audio; `sudo usermod -aG audio $USER` then log out and
  back in; check with `id -nG | grep -w audio` - documented for the reader, not
  run by Cline); (5) GUI smoke test now says the window opens only briefly and
  closes on its own, which is normal; (6) no times added - none were recorded in
  07; (7) repo-root note added once near the top of the commands (all commands
  from the repository root, except the uv/.NET/cl6x install steps); (8)
  unverified markers kept only on untested items (100-epoch training, other
  pedals). Docs only: no code, no setup-linux.sh, no README, no new
  dependencies.
- 08 plan written and owner-approved (docs/plans/08-dev-setup-linux.md; plan
  mode only, no code): check-only dev-setup-linux.sh at the repo root -
  required (exit 1 if missing): dotnet (PATH, else ~/.dotnet/dotnet counts
  with a warning), uv (must be on PATH), cl6x at
  <repo>/.tooling/cgt-8.3.1/ti-cgt-c6000_8.3.1/bin/cl6x (bank.py:21, :176);
  warnings only: ALSA header (both fixes printed), clang, gcc -m32 probe,
  libportaudio, audio group, snd_seq. [ OK ]/[WARNING]/[MISSING] lines with
  Why/Fix text; exit 0 = required present, 1 = any required missing; no code
  reuse from setup-linux.sh (mirrored idioms with line citations). Plus a
  message-only dotnet closing hint in setup-linux.sh after line 177 and the
  future docs/LINUX.md insertion points. Owner answers: audio group/snd_seq
  and ALSA header warning-only; tool checks limited to the owner's list.
- 08 IMPLEMENTED (act mode, exactly per docs/plans/08-dev-setup-linux.md):
  (1) new dev-setup-linux.sh at the repo root, chmod +x - check-only, `set -u`
  only (no set -e), no sudo, no network, installs nothing, never executes a
  printed fix; git/cmake/gcc/g++/ninja deliberately not checked (covered by
  setup-linux.sh:37-42, noted in comments). Required: dotnet (PATH, else
  ~/.dotnet/dotnet counts as present with a WARNING), uv (must be on PATH;
  ~/.local/bin-only still MISSING with the PATH hint as fix), cl6x at
  .tooling/cgt-8.3.1/ti-cgt-c6000_8.3.1/bin/cl6x (bank.py:21, :176). Warns:
  ALSA header (both fixes: libasound2-dev OR STOMP_PYTHON=3.12), clang,
  gcc -m32 probe, libportaudio, audio group, snd_seq (explicit note when
  /dev/snd is absent). Output: header line, aligned [ OK ]/[WARNING]/
  [MISSING] lines with Why:/Fix: blocks, `Result: PASS/FAIL` line; exit 0 =
  all required present, 1 = any missing. (2) setup-linux.sh: added only the
  message-only dotnet closing block after line 177's cl6x note (net +13
  lines; pure echoes, no exports, no PATH mutation). (3) docs/LINUX.md: added
  only the two planned insertions (+9 lines: one-line pointer after the
  repo-root paragraph; new "## Checking your setup (dev-setup-linux.sh)"
  subsection before "## Setting up (setup-linux.sh)"). Sandbox checks (all
  pass): `bash -n` rc=0 on both scripts; run prints
  `Result: FAIL (1 required item missing, 5 warnings)` with real exit 1
  (uv MISSING, cl6x OK); git status/diff show only these three files plus
  docs/STATUS.md. Owner must run on the host: `./dev-setup-linux.sh` (expects
  PASS; also answers the 32-bit libs <confirm>) and a rerun of
  `./setup-linux.sh` for the new closing message. No README/apps/tools/
  bank.py edits, no new dependencies, no sudo, no commit; stage 09 not
  started.
- 08c cosmetic fix (act mode): dev-setup-linux.sh version_of() (now lines
  59-64) keeps only the first line of `<tool> --version` output
  (`| head -n 1`). version_of is the script's only version capture (callers:
  dotnet line 71, uv line 103, clang line 131), so the clang OK line no
  longer prints clang's full 4-line --version output; dotnet and uv already
  print one line and are unchanged. No checks, classes, exit codes or output
  wording changed. Sandbox: `bash -n` rc=0; run identical to stage 08
  (`Result: FAIL (1 required item missing, 5 warnings)`, exit 1). Owner must
  rerun `./dev-setup-linux.sh` on the host to see the one-line clang OK.
- 10 Final v1 review and doc fixes (act mode): diff review against upstream
  conventions passed (docs/plans/10-final-review.md). docs/LINUX.md and
  docs/STATUS.md updated: 100-epoch training and bank install verified on
  MS-60B+ fw 1.20; footer issue verified; stage 09 marked DONE, stage 10 IN
  PROGRESS. Commands run: `git status --short`, `git diff --stat`,
  `bash -n setup-linux.sh`, `bash -n dev-setup-linux.sh`,
  `git ls-files -s setup-linux.sh dev-setup-linux.sh`,
  `grep -rn "/home/" $(git diff --name-only upstream/main...linux-port)`.
  No code changes, no build, no new dependencies, no sudo, no commit.
- 11 Clearer cl6x install instructions + LINUX.md tidy (act mode): reworded cl6x Fix message in dev-setup-linux.sh (TI archive link, full unattended install command with chmod +x and --prefix, per-part explanation, no-PATH and survives-restart note, one-line check, "no source files" note; dotnet and uv PATH notes now state per-window expiry and give ~/.bashrc lines). In docs/LINUX.md: rewrote cl6x section with same content, added per-window PATH notes and ~/.bashrc lines for dotnet and uv, moved 100-epoch training and GUI footer from "What does not work" to "What works" (Other pedals stays). No logic or behaviour changes; no setup-linux.sh, README, apps/, tools/ or bank.py edits; no new dependencies; no sudo; no commit.
- 11b Tidy two messages in dev-setup-linux.sh (act mode; per approved plan): uv Fix sentence now reads "add uv to this terminal's PATH:"; both dotnet Fix blocks print each export line only once, followed by the per-window-expiry sentence and one ~/.bashrc note. No logic or behaviour changes; no other files; no new dependencies; no sudo; no commit.
- 12a cl6x --prefix fix: DONE (act mode): docs/LINUX.md cl6x section and dev-setup-linux.sh cl6x Fix now use --prefix "$PWD/.tooling/cgt-8.3.1"; the TI installer appends ti-cgt-c6000_8.3.1 itself, so cl6x lands at .tooling/cgt-8.3.1/ti-cgt-c6000_8.3.1/bin/cl6x (bank.py:21). The installer is run from ~/Downloads by full path with the shell in the repo root, so the .bin never enters the repo; the one-line check is kept at that path. No logic changes, no other files, no .gitignore changes, no sudo, no commit.

## Known issues / open questions
- Stage 08 host verification: verified on a separate machine (owner): `./dev-setup-linux.sh`
  should report PASS on the host (that run also answers the 32-bit libs
  `<confirm>` in Environment below), and a rerun of `./setup-linux.sh` should
  print the new dotnet closing note. Sandbox-only run: FAIL, exit 1, as
  expected (uv not on PATH in the sandbox).
- Sandbox observation from the stage 08 run: $HOME in this environment holds
  `~/.dotnet/dotnet` and `~/.local/bin/uv` although neither is on PATH, so
  the script reports dotnet as [WARNING] (present, not on PATH - the plan's
  designed fallback) and uv as [MISSING] (setup-linux.sh:38 needs
  `command -v uv`); Environment's "Missing: clang, dotnet, uv" means "not on
  PATH". ALSA header and /dev/snd/seq are present here, contrary to the
  plan's sandbox prediction ("unknown" / "likely missing").
- python-rtmidi (pinned ==1.5.8, also the latest PyPI release) has no CPython 3.13
  wheel. On the default STOMP_PYTHON=3.13, uv compiles the sdist, which needs
  /usr/include/alsa/asoundlib.h (Debian/Ubuntu: libasound2-dev, install by hand).
  setup-linux.sh checks for the header and stops with that message; run with
  STOMP_PYTHON=3.12 to install from a prebuilt manylinux wheel instead.
- The train venv pulls in sounddevice (NAM dependency), whose import needs
  libportaudio; setup-linux.sh only warns if `ldconfig -p` does not show it.
  Training itself does not use sounddevice.
- crcmod (stomphacks requirement) has no version pin anywhere upstream.
- First host run of setup-linux.sh failed at patches/stomphacks-catalogue.patch:
  upstream zoom-zt2 is committed with CRLF while the patches are LF, so plain
  `git apply` refused the hunks. Fixed by adding `--ignore-whitespace` to all
  `git apply` calls in ensure_checkout (script later completed on host).
- 06a host verification (no dotnet in sandbox for Cline): DONE - owner ran
  `dotnet build` and both `--smoke-test` (two OK lines from a source checkout:
  backend runtime, then training runtime) and `--gui-smoke-test` (X11); pass.
- Hardware: verified on MS-60B+ fw 1.20 via CLI and GUI (06b). The pedal currently holds the 3-model, 10-epoch test bank (installed via the GUI in 06b).
- GUI footer text: code change done in stage 09 (StudioLayout.cs:315 branches on OperatingSystem.IsLinux(); Linux shows the USB-MIDI verified note; Windows/macOS unchanged). Verified per owner report on MS-60B+ fw 1.20 (saves in a patch, survives reboot); host GUI build optional final confirmation.
- See docs/SPEC.md "Open questions".

## Last Cline report
Stage 11b tidy two messages in dev-setup-linux.sh (act mode; per approved plan).
Files changed: dev-setup-linux.sh (uv Fix sentence now reads "add uv to this terminal's PATH:"; both dotnet Fix blocks print each export line only once, then the per-window-expiry sentence, then one ~/.bashrc note).
Commands run: `bash -n dev-setup-linux.sh`, `git status --short`, `git diff --stat`.
No logic or behaviour changes; no other files; no new dependencies; no sudo; no commit; next stage not started.
