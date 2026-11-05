# Audio-only FFmpeg

The release uses an unmodified FFmpeg 7.1 audio-only build under LGPL-2.1-or-later,
not the much larger GPL essentials binary distributed by imageio-ffmpeg.
Place the resulting `ffmpeg.exe` in this directory before building the application.
It runs as a separate process and users may replace it.

Source: https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz

Build tools for Windows: Zig 0.15.2, GNU Make 4.4.1, Git Bash. See
`build_ffmpeg.sh` for the exact configure flags. After extracting source,
run the script from the source directory with these tools on PATH.
If object stripping does not support PE, use `ffmpeg_g.exe` unchanged.

For binary distribution retain LGPL license texts, the matching source archive,
this build script and the configure/build information. Qt/PySide matching source
archives and copyright notices also belong in the binary's Licenses folder.
Third-party library sources are separate from the application's MIT source.
