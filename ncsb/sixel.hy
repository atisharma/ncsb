"""
Show a sixel image.
"""

(try
  (import libsixel.encoder [Encoder SIXEL_OPTFLAG_WIDTH SIXEL_OPTFLAG_COLORS])
  (except [ImportError]
    (setv Encoder None)))

(defn show [fname width * [colors 256]] 
  (when (and fname Encoder)
    (setv encoder (Encoder))
    (encoder.setopt SIXEL_OPTFLAG_WIDTH f"{width :d}")
    (encoder.setopt SIXEL_OPTFLAG_COLORS f"{colors :d}")
    (encoder.encode fname)))
