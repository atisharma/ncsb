"An experimental LMS browser.

A S Sharma (C) 2021
Licensed under the GNU GENERAL PUBLIC LICENSE v3

Press ? for help.

Each pane (mode) has its own display and loop.


players pane
------------

  1. player | currently playing | on/off
  2. player | currently playing | on/off
* 3. player | currently playing | on/off
  4. player | currently playing | on/off


playlist pane
--------------

player | on/off | volume

playlist
  1. ...
  2. ...
* 3. ...  (show % complete)
  4. ...


search pane
-----------
(selection replaces (p, <ret>), appends to (a) or inserts (i) in playlist)

"


(import curses)
(import [requests.exceptions [ConnectionError]])

(import display)
(import [lms-controller :as lms])
(import [screen [screen]])
(import [util [get-in]])
(import sixel)

(setv debug False)

(setv copyright "(c) ncsb authors 2021")

(defn server-help []
 ["q        -   quit"
  "r        -   redraw screen"
  ""
  "j/k      -   down/up in player list"
  "g/G      -   first/last in player list"
  ""
  "l/<ret>  -   show player playlist"
  "<space>  -   pause/unpause selected layer"
  "p        -   power on/off selected player"
  ""
  "?        -   show this help"])

(defn player-help []
 ["qh       -   back to players"
  "r        -   redraw screen"
  "c        -   toggle cover art display"
  ""
  "j/k      -   selection down/up in playlist"
  "g/G      -   selection first/last in playlist"
  ""
  "+/-      -   volume up/down"
  "s        -   stop player"
  "<space>  -   pause/unpause player"
  "p        -   toggle power"
  ""
  "<ret>    -   play selected song"
  "J/K      -   skip/previous in playlist"
  "M/m      -   move selected song up/down in playlist"
  "S        -   shuffle off/songs/albums"
  "R        -   repeat off/song/playlist"
  "C        -   clear playlist"
  "x        -   remove selected song from playlist"
  ""
  "A        -   text search for artists"
  "B        -   text search for albums"
  "/        -   text search for tracks"
  ""
  "b        -   albums by artist of selected song"
  "t        -   tracks by artist of selected song"
  "o        -   tracks on album of selected song"
  ""
  "?        -   show this help"])

(defn search-help []
 ["qh       -   back to playlist"
  "r        -   redraw screen"
  ""
  "j/k      -   down/up in search results"
  "g/G      -   first/last in search results"
  ""
  "a        -   add selected item to end of playlist"
  "i        -   insert selected item in playlist"
  "p/<ret>  -   replace playlist with selected item"
  ""
  "//l      -   contextual search on selected item"
  ""
  "?        -   show this help"])


(defn server-loop [stdscr &kwonly server-ip port]
 "Main event loop showing all players."
 (global debug)
 (setv running True
       sel 0)
 (with [server (lms.Server server-ip port)]
  (with [scr (screen stdscr :nodelay False :halfdelay 10)]
   (while running
    (try
     (setv players (.players lms server))
     (setv player (get players sel "playerid"))
     (.players display scr players sel :debug debug)
     (.server display scr f"LMS v{(.version lms server)}")
     (.track display scr (.title lms server player) (.artist lms server player) (.album lms server player))
     (.refresh scr)
     (setv c (.getkey scr))
     (cond [(none? c)]
           [(= c "?") (help-loop scr (server-help))]
           [(= c "q") (setv running False)]
           [(= c "r") (.clear scr)]
           [(= c "j") (setv sel (% (inc sel) (len players)))]
           [(= c "k") (setv sel (% (dec sel) (len players)))]
           [(= c "g") (setv sel 0)]
           [(= c "G") (setv sel (dec (len players)))]
           [(= c " ") (.pause lms server player)]
           [(= c "p") (.power lms server player "toggle")]
           [(= c "D") (setv debug (not debug))]
           [(in c "l\n") (player-loop scr server player)])
     (except [KeyboardInterrupt] (setv running False))
     (except [e [LMSError]] (.message display scr e)))))))


(defn player-loop [scr server player]
 "Event loop showing selected player and playlist."
 (global debug)
 (setv running True
       sel 0
       cover {:show False :coverid None :sixel None :displayed False :filename None :prev-track-id None})
 (.clear scr)
 (while running
  (setv status (.status lms server player))
  (setv player-name (get status "player_name"))
  (setv playlist (get-in status "playlist_loop"))
  (setv shuffle (get status "playlist shuffle"))
  (setv repeat_ (get status "playlist repeat"))
  (setv track-count (get status "playlist_tracks"))
  (.player display scr status :debug debug)
  (.playlist display scr status sel :debug debug)
  (.track display scr (.title lms server player) (.artist lms server player) (.album lms server player))
  ; it is unknown why printing on y=1 interacts with the cover art to print in the wrong place
  (unless (:show cover) (.server display scr f"LMS v{(.version lms server)}"))
  (.refresh scr)
  (setv sel (% sel (len playlist)))
  (setv c (.getkey scr))
  (cond [(none? c)]
        [(= c "?") (help-loop scr (player-help))]
        [(in c "qh") (setv running False)]
        [(= c "r") (.clear scr) (.refresh scr) (assoc cover :displayed False)]
        [(= c "c") (.clear scr) (assoc cover :show (not (:show cover)))]
        [(= c "g") (setv sel 0)]
        [(= c "G") (setv sel (dec (len playlist)))]
        [(= c "+") (.volume-change lms server player 2)]
        [(= c "-") (.volume-change lms server player -2)]
        [(= c " ") (.pause lms server player)]
        [(= c "A") (search-loop scr server player player-name "artists" (+ "search:" (.input scr "search artists")))]
        [(= c "B") (search-loop scr server player player-name "albums" (+ "search:" (.input scr "search albums")))]
        [(= c "/") (search-loop scr server player player-name "songs" (+ "search:" (.input scr "search songs")))]
        [(= c "s") (.stop lms server player)]
        [(= c "p") (.power lms server player "toggle")]
        [(= c "S") (.playlist-shuffle lms server player (% (+ 1 shuffle) 3))]
        [(= c "R") (.playlist-repeat lms server player (% (+ 1 repeat_) 3))]
        [(= c "C") (.playlist-clear lms server player)]
        [(= c "D") (setv debug (not debug))])
  (when playlist
   (setv selected-track (get playlist (% sel (len playlist))))
   (setv selected-index (get selected-track "playlist index"))
   (setv current-index (int (or (get-in status "playlist_cur_index") 0)))
   (setv current-track (first (filter (fn [track] (= (get track "playlist index") current-index)) playlist)))
   (update-coverart scr server current-track cover)
   (cond [(none? c)]
         [(= c "j") (setv sel (% (inc sel) (len playlist)))]
         [(= c "k") (setv sel (% (dec sel) (len playlist)))]
         [(= c "M") (.playlist-move-up lms server player selected-index) (setv sel (% (dec sel) (len playlist)))]
         [(= c "m") (.playlist-move-down lms server player selected-index) (setv sel (% (inc sel) (len playlist)))]
         [(= c "J") (.playlist-skip lms server player)]
         [(= c "K") (.playlist-prev lms server player)]
         [(= c "\n") (.playlist-play-index lms server player (get playlist sel "playlist index"))]
         [(= c "x") (.playlist-delete lms server player (get selected-track "playlist index"))]
         [(= c "b") (search-loop scr server player player-name "albums" f"artist_id:{(get-in selected-track \"artist_id\")}")]
         [(= c "t") (search-loop scr server player player-name "songs" f"artist_id:{(get-in selected-track \"artist_id\")}")]
         [(= c "o") (search-loop scr server player player-name "songs" f"album_id:{(get-in selected-track \"album_id\")}")])))
 (.clear scr))


(defn search-loop [scr server player player-name kind term]
 "Search the library and add/insert/replace playlist."
 (global debug)
 (when term
  (setv running True
        sel 0)
  (setv (, loop-kind control-kind) (cond [(= kind "artists") (, "artists_loop" "artist")]
                                         [(= kind "albums") (, "albums_loop" "album")]
                                         [(= kind "songs") (, "titles_loop" "track")]
                                         [(= kind "genres") (, "genres_loop" "album")]
                                         [(= kind "playlists") (, "playlists_loop" "album")]))
  (setv results (get-in (.search lms server player kind term) loop-kind))
  (.clear scr)
  (when results
   (while running
    (.search-results display scr player-name results (second (.split term ":")) kind sel :debug debug)
    (setv selected-result (get results (% sel (len results))))
    (.refresh scr)
    (setv c (.getkey scr))
    (cond [(none? c)]
          [(= c "?") (help-loop scr (search-help))]
          [(in c "qh") (setv running False)]
          [(= c "r") (.clear scr)]
          [(= c "g") (setv sel 0)]
          [(= c "G") (setv sel (dec (len playlist)))]
          [(= c "j") (setv sel (% (inc sel) (len results)))]
          [(= c "k") (setv sel (% (dec sel) (len results)))]
          [(= c "D") (setv debug (not debug))]
          [(in c "l/") (cond [(= kind "artists") (search-loop scr server player player-name "albums" f"artist_id:{(get-in selected-result \"id\")}")]
                             [(= kind "albums") (search-loop scr server player player-name "songs" f"album_id:{(get-in selected-result \"id\")}")]
                             [(= kind "songs") (search-loop scr server player player-name "artists" f"track_id:{(get-in selected-result \"id\")}")])]
          [(in c "aip\n") (.playlist-control lms server player
                           (get selected-result "id")
                           :action (cond [(= c "a") "add"]
                                         [(= c "i") "insert"]
                                         [:else "load"])
                           :kind control-kind)
                         (setv running False)])))))


(defn help-loop [scr help-text]
 "Show some help text."
 (setv running True)
 (.clear scr)
 (while running
  (.help display scr help-text)
  (.message display scr copyright)
  (.refresh scr)
  (setv c (.getkey scr))
  (cond [(none? c)]
        [:else (setv running False)])))


(defn update-coverart [scr server track cover]
 "Fetch/show the cover art of the current track."
 ; cover {:coverid None :sixel None :last-coverid None :fresh False :filename ".."}
 ; get new cover art on new track
 (when (:show cover)
  (unless (= (:coverid cover) (get-in track "coverid"))
   (assoc cover :coverid (get-in track "coverid")
                :filename f"/tmp/ncsb-cover-{(:coverid cover)}.png"
                :displayed False)
   (.coverart server (:coverid cover) 160 160 :fname (:filename cover)))
  (unless (and (:displayed cover) (= (:prev-track-id cover) (get-in track "id")))
   (try
    ; this causes a visible flash but gets the cursor in the right place
    (.locate-coverart display scr)
    (-> cover
     (:filename)
     (sixel.show 160)
     (display.coverart))
    (assoc cover :displayed True :prev-track-id (get-in track "id"))
    (except [RuntimeError])))))


(defn main [&kwonly server-ip port]
 "Main entry point.
 The command-line tool is in python because hy does not handle sigwinch, which
 breaks resizing in curses."
 (.wrapper curses server-loop :server-ip server-ip :port port))
 
