# Contrast

`scripts/brandio.py` enforces this. The constants live at the top of that file. Change a number there and here together.

Distances are CIE76 (ΔE76). That is a heuristic so a broken pair gets caught before a person looks. It is not a colorblindness certification. The proof PNGs are the review.

| Check | Constant | Result |
| --- | --- | --- |
| Ink on background | `INK_CONTRAST_MIN` 4.5 | Fail below 4.5:1 |
| Series color on background | `SERIES_CONTRAST_MIN` 3 | Fail below 3:1. The bar disappears |
| Two series colors | `SERIES_DELTA_E_FAIL` 18, `SERIES_DELTA_E_WARN` 28 | Fail below 18. Warn from 18 up to 28 |
| Series color near negative | `SERIES_DELTA_E_WARN` 28 | Warn. It will be read as a loss |
| Positive vs negative | `SIGN_DELTA_E_MIN` 25 | Fail below 25 |
| Positive is also a series color | — | Warn. Do not use both meanings on the same axes |
| Accent and negative are the same hue | — | Warn. One meaning per chart |
| Accent is also a series color | — | Warn |
| Mark wash on the background is under 3:1 | `SERIES_CONTRAST_MIN` | Warn. A wash, not a bar |
| More than 6 series colors | — | Warn |
| More than 12 series colors | — | Fail |

`write_matplotlibrc.py` writes nothing when a check fails. `--force` writes anyway and only after a person accepts the specific failure. `--force` does not approve an unconfirmed proposal. That is `--confirm`, and only after they say so.

## Type and fills

Put labels in the ink color, outside the mark. A fill can clear 3:1 against the background and still fail 4.5:1 for type sitting on it. Do not put white or ink type inside a bar unless you measured that pair at 4.5:1 or better.

`roles.mark` is a highlighter. It is not a series, a bar, or a line.

Sequential steps are a ramp from background toward primary. The light end will not clear 3:1. Use the ramp for one quantity, not as categories.

## One hue, one meaning

A color that encodes "this series" cannot also encode "this is bad" or "look here" on the same axes. Split the chart or change the encoding. Position and the printed number carry the value. Color is the second channel, not the only one.
