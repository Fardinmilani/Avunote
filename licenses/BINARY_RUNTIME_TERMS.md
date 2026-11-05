# Binary runtime components

Voxriva application source is MIT, copyright 2026 Fardin Milani. This does not
relicense third-party native components.

The bundled Intel OpenMP `libiomp5md.dll` comes unchanged from Intel's official
`intelopenmp.redist.win` NuGet package, version `2025.3.0.640`, under the
**Intel Simplified Software License, October 2022**. The package's full license,
copyright metadata, third-party-program notices and exact-file provenance are
included in `Intel-OpenMP-Redistributable-2025.3.0.640`.

That license permits use and redistribution of the unmodified Intel binary
with its required notices. Its restrictions on modification, reverse engineering,
decompilation and disassembly apply to that Intel binary component under its
own terms, not to Voxriva's MIT source or to other libraries. Intel names must
not be used to imply endorsement. See the complete component license for all
terms and applicable third-party exceptions.

Qt/PySide and the slim FFmpeg component retain their own LGPL rights, including
permitted library replacement/relinking and relevant debugging rights. No
application-wide restriction is intended to override those rights. Their matching
source archives and notices are in the release's `Licenses` directory.

Model licenses are recorded separately per catalog entry and in
`THIRD_PARTY_NOTICES.md`; the application's MIT license is not their license basis.
