# Avunote · آوونوت

Avunote is the new name of this local speech transcription and AI conversation
application. The coined name suggests **آوا / voice + note**; the Persian form is
**آوونوت**. The proposed website address is **avunote.com**.

## Name and domain checks

Checked on **5 November 2026, approximately 21:15 UTC**. These are observations at
the time of the check, rather than a guarantee of future availability.

- Exact web searches for `"Avunote"`, `"Avunote.com"`, `"Avunote" software voice
  transcription`, and `"Avunote" trademark` returned no indexed exact brand
  matches. This does not establish that every unindexed use or trademark is absent.
- An HTTPS request to the [.com registry's authoritative Verisign RDAP
  endpoint](https://rdap.verisign.com/com/v1/domain/avunote.com) returned **HTTP
  404** with `Content-Type: application/rdap+json`: no registered domain record was
  found for `avunote.com` at that time.
- Positive controls used the same Node.js HTTPS request method and endpoint:
  [voxriva.com](https://rdap.verisign.com/com/v1/domain/voxriva.com) and
  [example.com](https://rdap.verisign.com/com/v1/domain/example.com) both returned
  **HTTP 200** with their correct registered domain names. The Voxriva record
  reported registration on 20 October 2026.
- No domain was purchased or registered. The suggested address is not yet an
  owned or published application website. Recheck availability at registration.
- This check is not comprehensive trademark clearance; no exclusive legal rights
  in the name are asserted by these search results.

Other candidates with existing indexed uses were discarded, including Nuvyra,
Velunex, Avorune, Neravox, Velqora, Avunera, Oruniva, and Nuvareli.

## Visual identity

The mark combines an indigo circular chat/letter shape and three cyan waveform
capsules. Its outside shape and center are transparent: Windows displays the
freeform mark without a solid square tile. The horizontal lockup uses the exact
word **Avunote** in dark indigo.

| Asset | Purpose |
| --- | --- |
| [`assets/avunote-mark.png`](../assets/avunote-mark.png) | 1024 × 1024 transparent mark |
| [`assets/avunote.ico`](../assets/avunote.ico) | Windows icon with 16, 20, 24, 32, 40, 48, 64, 96, 128, and 256 px frames |
| [`assets/avunote-logo-transparent.png`](../assets/avunote-logo-transparent.png) | Horizontal transparent logo, 2116 × 584 px |
| [`assets/avunote-brand-preview.png`](../assets/avunote-brand-preview.png) | Mark and lockup preview on white and dark backgrounds |

The mark works on light and dark surfaces. Use a light text treatment for the
wordmark on a dark surface; the supplied lockup's dark lettering suits light
surfaces. Preserve transparency and aspect ratio, and leave clear space around
the artwork.

The approved raster mark and horizontal lockup were produced with the built-in
ImageGen tool. The lockup prompt preserved the approved mark, specified the exact
text `Avunote`, a bold geometric sans-serif, dark indigo `#4939B8`, and a transparent
background with no tile, glow, shadow, slogan, or watermark.

[`scripts/build_brand_assets.py`](../scripts/build_brand_assets.py) mechanically
frames/resizes the approved PNG inputs and encodes the multi-size ICO using the
application's existing PySide6 dependency. Every ICO frame was decoded and checked;
the final PNG corners have alpha zero. The source artwork is not represented as a
vector master.
