# Publishing Avunote updates

Avunote checks the latest stable public release of `Fardinmilani/Avunote`. The
repository was renamed from `Fardinmilani/Voxriva`; the updater still accepts that
former API name, GitHub redirects (including `/repositories/<id>/releases/latest`),
and Setup download URLs that keep `/Voxriva/` in the path. No published stable
release is treated as up to date, not as a failure. The release tag must match
`VERSION` with an optional lowercase `v` prefix, for example `v2.4.0`. Checks
start only from a Windows Setup installation. Set `AVUNOTE_DISABLE_UPDATES=1` to
disable them in managed or offline environments.

Run `BUILD_SETUP.cmd` and attach these build outputs to the matching GitHub Release.

- `Avunote-<version>-Windows-x64-Setup.exe`
- `Avunote-<version>-Windows-x64-Setup.exe.sha256.txt` for manual verification
- `Avunote-<version>-Windows-x64-Manifest.json` for building subsequent smaller updates

To make a smaller update, keep the previous release's manifest in `release/`. The next
local build chooses the newest earlier manifest automatically. You can also choose a
specific baseline.

```powershell
.\BUILD_SETUP.cmd -PreviousManifest .\release\Avunote-2.4.0-Windows-x64-Manifest.json
```

For the Windows GitHub Actions build, provide the previous published tag as the
`previous_release_tag` workflow input.

This builds the full Setup and, when smaller, an additional
`Avunote-<new>-Windows-x64-Update-from-<old>-<baseline-sha256>.exe`. Attach it unchanged,
along with its checksum sidecar. This installer contains changed files and the new
release manifest. The build falls back to full Setup when payload files were removed.
The manifest fingerprint in its filename ties the update to the exact previous
Windows build. Users with skipped releases, modified app files, or missing baseline
manifests receive the full Setup. Neither package includes models, recordings or chats.

The app uses the SHA-256 reported by the official GitHub Releases API and verifies
both the file length and digest. An executable without that digest is ineligible for
automatic installation. Downloads start only on request. After downloading, select
**Restart and install** to close the app normally, apply the verified package to the
same installation directory, and launch the updated app. The model cache and local
profile remain in their existing locations.
