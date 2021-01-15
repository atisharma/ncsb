"""
Show a sixel image.
"""

(import [libsixel.encoder [Encoder SIXEL_OPTFLAG_WIDTH SIXEL_OPTFLAG_COLORS]])

(defn show [fname width &kwonly [colors 256]] 
 (setv encoder (Encoder))
 (encoder.setopt SIXEL_OPTFLAG_WIDTH f"{width :d}")
 (encoder.setopt SIXEL_OPTFLAG_COLORS f"{colors :d}")
 (encoder.encode fname))
