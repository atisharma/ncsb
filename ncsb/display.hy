"""
Display panes for the LMS browser.

"""

; some useful unicode symbols
"▶️ ⏸️ ⏯️ ◀️ ⏹️ ⏪️ ⏩️ ⏮️ ⏏️ 🔀️ 🔁️ 🔃️ 🔂️ ℹ️ 🔄️ ⏻ ⏼ ⏽ ⭘ ⏾ 🔊"

(import [util [get-in]])

(setv main-panel-y 9)
(setv main-panel-x 2)
(setv server-y 1)
(setv server-x 2)
(setv title-y 1)
(setv msg-x 2)
(setv info-panel-y 30)
(setv info-panel-x 2)


(defn server [scr s]
 "Some information about the LMS server."
 (.put scr server-y server-x s))

(defn players [scr player-list sel &kwonly [debug False]]
 "Show the players in the player list."
 (for [(, y p) (enumerate player-list)]
  (setv player-name (get p "name"))
  (when (= sel y) (.put scr title-y (.centre scr player-name) player-name :style scr.curses.A_BOLD :col 5))
  (setv style (if (= sel y) scr.curses.A_BOLD scr.curses.A_NORMAL))
  (.put scr (+ y main-panel-y) main-panel-x "•" :col (if (get p "connected") 3 2))
  (.put scr (+ y main-panel-y) (+ 2 main-panel-x) "⏼" :col (if (get p "power") 3 2))
  (.put scr (+ y main-panel-y) (+ 4 main-panel-x) (if (get p "isplaying") "▶️ " "⏹️ ") :col (if (get p "isplaying") 3 2))
  (.put scr (+ y main-panel-y) (+ 6 main-panel-x) f" {player-name :<20}" :style style)
  (when (and debug (= sel y) (debug-info scr p)))))

(defn player [scr status &kwonly [debug False]]
 "Display for the current player."
 (setv player-name (get status "player_name"))
 (setv mode (get status "mode"))
 (setv volume (get status "mixer volume"))
 (setv wifi (get status "signalstrength"))
 (setv shuffle (get status "playlist shuffle"))
 (setv repeat_ (get status "playlist repeat"))
 (.put scr title-y (.centre scr player-name) player-name :style scr.curses.A_BOLD :col 5)
 (.put scr (+ 1 server-y) (+ 0 server-x) f"🔊{volume :3.0f}%")
 (.put scr (+ 1 server-y) (+ 8 server-x) (cond [(= mode "play") "▶️ "]
                                               [(= mode "stop") "⏹️ "]
                                               [(= mode "pause") "⏸️ "]))
 (when repeat_ (.put scr (+ 1 server-y) (+ 10 server-x) (cond [(= repeat_ 2) "🔁️"]
                                                              [(= repeat_ 1) "🔂️"]
                                                              [:else ""])))
 (when shuffle (.put scr (+ 1 server-y) (+ 13 server-x) (cond [(= shuffle 2) "🔀️"]
                                                              [(= shuffle 1) "a🔀️"]
                                                              [:else ""])))
 (when wifi (.put scr (+ 2 server-y) (+ 0 server-x) f"wifi {wifi :3d}%"))
 (when debug (debug-info scr status)))

(defn playlist [scr status sel &kwonly [debug False]]
 "Display for the current player's playlist."
 (setv mode (get status "mode"))
 (setv playlist (get-in status "playlist_loop"))
 (setv y-offset (min 0 (- (.bottom scr) (+ main-panel-y sel 1)))) 
 (when playlist
  (setv elapsed (/ (or (int (get-in status "time")) 0) (or (get-in status "duration") Inf)))
  (for [(, y track) (enumerate playlist)]
   (when (>= (+ y y-offset) 0)
    (setv style (if (= sel y) scr.curses.A_BOLD scr.curses.A_NORMAL))
    (setv is-current (= (int (get status "playlist_cur_index")) (int (get track "playlist index"))))
    (setv elapsed-str (if is-current f"[{(* 100 elapsed) :2.0f}%]" ""))
    (setv col (if is-current (cond [(= mode "play") 3]
                                   [(= mode "stop") 2]
                                   [(= mode "pause") 4]
                                   [:else 5])
                           0))
    (.put scr (+ y y-offset main-panel-y) main-panel-x
     f"{(get track \"playlist index\") :>2d} - {(get track \"title\") :<40}"
     :col col
     :style style)
    (.put scr (+ y y-offset main-panel-y) (min (- (.right scr :s elapsed-str) 2) 100)
     f"{elapsed-str}"
     :col col
     :style style))
   (when (= sel y)
    (.put scr (- main-panel-y 2) (+ 1 main-panel-x)
     (.join " - " (list (map str (remove none? (map get-in (repeat track) ["artist" "album" "tracknum" "bitrate" "type"])))))
     :style (| scr.curses.A_ITALIC scr.curses.A_BOLD))) 
   (when (and (= sel y) debug)
    (debug-info scr track :y0 main-panel-y :x0 (+ 100 main-panel-x))))))

(defn search-results [scr player-name results term kind sel &kwonly [debug False]]
 "Display search results."
 (.put scr title-y (.centre scr player-name) player-name :style scr.curses.A_BOLD :col 5)
 (.put scr (+ 2 title-y) (.centre scr "search") "search" :style scr.curses.A_BOLD :col 191)
 (.put scr (+ 3 title-y) (.centre scr term) term :style (| scr.curses.A_ITALIC scr.curses.A_BOLD) :col 191)
 (.put scr (+ 4 title-y) (.centre scr f"in {kind}") f"in {kind}" :style scr.curses.A_BOLD :col 191)
 (setv y-offset (min 0 (- (.bottom scr) (+ main-panel-y sel 1)))) 
 (for [(, y result) (enumerate results)]
  (when (>= (+ y y-offset) 0)
   (setv style (if (= sel y) scr.curses.A_BOLD scr.curses.A_NORMAL))
   (setv artist (get-in result "artist"))
   (setv album (get-in result "album"))
   (setv track (get-in result "title"))
   (setv genre (get-in result "genre"))
   (cond [track 
          (.put scr (+ -2 y y-offset main-panel-y) main-panel-x track :style style)
          (.put scr (+ -2 y y-offset main-panel-y) (+ 3 main-panel-x (len track)) album :style style :col 5)
          (.put scr (+ -2 y y-offset main-panel-y) (+ 6 main-panel-x (len track) (len album)) artist :style style :col 4)]
         [album (.put scr (+ -2 y y-offset main-panel-y) (.centre scr album) album :style style)]
         [artist (.put scr (+ -2 y y-offset main-panel-y) (.centre scr artist) artist :style style)])
   (when debug (debug-info scr track)))))

(defn browse-results [scr player-name results sel &kwonly [debug False] [parent "music folder"]]
 "Display search results."
 (.put scr title-y (.centre scr player-name) player-name :style scr.curses.A_BOLD :col 5)
 (.put scr (+ 2 title-y) (.centre scr "search") parent :style scr.curses.A_BOLD :col 191)
 (setv y-offset (min 0 (- (.bottom scr) (+ main-panel-y sel 1)))) 
 (for [(, y result) (enumerate results)]
  (when (>= (+ y y-offset) 0)
   (setv style (if (= sel y) scr.curses.A_BOLD scr.curses.A_NORMAL))
   (setv kind (get-in result "type"))  ; folder or track
   (setv filename (get-in result "filename"))
   (if (= kind "track")
    (.put scr (+ -2 y y-offset main-panel-y) main-panel-x filename :style style :col 4)
    (.put scr (+ -2 y y-offset main-panel-y) main-panel-x filename :style style))
   (when debug (debug-info scr result)))))

(defn track [scr title album artist]
 "Display current playlist item."
 (when title (.put scr (+ 2 title-y) (.centre scr title) title))
 (when artist (.put scr (+ 3 title-y) (.centre scr artist) artist))
 (when album (.put scr (+ 4 title-y) (.centre scr album) album)))

(defn help [scr lines]
 "Display long text in the main panel."
 (for [(, y line) (enumerate lines)]
  (.put scr (+ y title-y) main-panel-x line))) 

(defn coverart [sixel-string]
 "Display the cover art via sixel.
 We bypass curses and print directly to screen in the desired position."
 (when sixel-string
  (print sixel-string)))

(defn locate-coverart [scr]
 "Dirty hack to place cover art in the right place."
 (.put scr 1 (- (.right scr) 12) " ")
 (.refresh scr))

(defn message [scr msg]
 "Write a message."
 (.put scr (.bottom scr) msg-x msg))

(defn debug-info [scr records &optional [x0 info-panel-x] [y0 info-panel-y]]
 "Dump a list of dicts for debugging."
 (if (instance? dict records) (for [(, y (, k v)) (enumerate (sorted (.items records)))]
                               (.put scr (+ y y0) x0 k)
                               (.put scr (+ y y0) (+ 30 x0) v))
  (for [(, y r) (enumerate records)]
   (.put scr (+ y y0) x0 (sorted (.items r))))))
