#!/usr/bin/env bash
set -eu
./configure --disable-everything --disable-autodetect --disable-doc --disable-network \
 --disable-gpl --disable-version3 --enable-ffmpeg --disable-ffplay --disable-ffprobe \
 --disable-avdevice --disable-postproc --disable-x86asm --disable-asm \
 --enable-static --disable-shared --enable-w32threads --target-os=mingw32 --arch=x86_64 \
 --cc='zig cc -target x86_64-windows-gnu -mcpu=baseline' \
 --ld='zig cc -target x86_64-windows-gnu -mcpu=baseline' --ar='zig ar' --ranlib='zig ranlib' \
 --enable-demuxer=wav,mp3,mov,ogg,flac \
 --enable-decoder=pcm_s16le,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,pcm_s16be,pcm_s24be,pcm_s32be,pcm_u8,pcm_alaw,pcm_mulaw,mp3,mp3float,aac,aac_fixed,alac,vorbis,opus,flac \
 --enable-parser=aac,mpegaudio,opus,vorbis,flac \
 --enable-encoder=pcm_s16le --enable-muxer=wav --enable-protocol=file \
 --enable-filter=aresample,aformat,anull
make -j2 SHELL=sh V=1 ffmpeg_g.exe
cp ffmpeg_g.exe ffmpeg.exe
