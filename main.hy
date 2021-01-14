"An experimental LMS browser.

Each pane (mode) has its own display and loop.


Keys
====

j/k       up/down
h/l       prev/next pane
<return>  select
<space>   pause/toggle
/         search


UI
==

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
(selection replaces, appends to or inserts in playlist)

"

; TODO: vim-style commands


(import curses)

(import display)
(import [lms-controller :as lms])
(import [screen [screen]])
(import [util [get-in]])


(setv debug False)


(defn server-loop [stdscr &kwonly server-ip port]
 "Main event loop showing all players."
 (global debug)
 (setv running True
       sel 0)
 (with [server (lms.Server server-ip port)]
  (with [scr (screen stdscr :nodelay False)]
   (.halfdelay curses 5)
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
           [(= c "q") (setv running False)]
           [(= c "r") (.clear scr)]
           [(= c "j") (setv sel (% (+ sel 1) (len players)))]
           [(= c "k") (setv sel (% (- sel 1) (len players)))]
           [(= c "g") (setv sel 0)]
           [(= c "G") (setv sel (- (len players) 1))]
           [(= c " ") (.pause lms server player)]
           [(= c "p") (.power lms server player "toggle")]
           [(= c "D") (setv debug (not debug))]
           [(in c "l\n") (player-loop scr server player)])
     (except [KeyboardInterrupt] (setv running False)))))))


(defn player-loop [scr server player]
 "Event loop showing selected player and playlist."
 (global debug)
 (setv running True
       sel 0)
 (.clear scr)
 (while running
  (setv status (.status lms server player))
  (setv playlist (get-in status "playlist_loop"))
  (setv shuffle (get status "playlist shuffle"))
  (setv repeat_ (get status "playlist repeat"))
  (setv player-name (get status "player_name"))
  (.player display scr status :debug debug)
  (.playlist display scr status sel :debug debug)
  (.track display scr (.title lms server player) (.artist lms server player) (.album lms server player))
  (.server display scr f"LMS v{(.version lms server)}")
  ;(.message display scr (asctime))
  (.refresh scr)
  (setv c (.getkey scr))
  (cond [(none? c)]
        [(in c "qh") (setv running False)]
        [(= c "r") (.clear scr)]
        [(= c "g") (setv sel 0)]
        [(= c "G") (setv sel (- (len playlist) 1))]
        [(= c "+") (.volume-change lms server player 2)]
        [(= c "-") (.volume-change lms server player -2)]
        [(= c " ") (.pause lms server player)]
        [(= c "a") (search-loop scr server player player-name "artists" (.input scr "search artists"))]
        [(= c "b") (search-loop scr server player player-name "albums" (.input scr "search albums"))]
        [(= c "/") (search-loop scr server player player-name "songs" (.input scr "search songs"))]
        [(= c "s") (.stop lms server player)]
        [(= c "S") (.playlist-shuffle lms server player (% (+ 1 shuffle) 3))]
        [(= c "R") (.playlist-repeat lms server player (% (+ 1 repeat_) 3))]
        [(= c "C") (.playlist-clear lms server player)]
        [(= c "D") (setv debug (not debug))])
  (when playlist
   (setv selected-track (get playlist (% sel (len playlist))))
   (setv current-index (int (or (get-in status "playlist_cur_index") 0)))
   (setv current-track (first (filter (fn [track] (= (get track "playlist index") current-index)) playlist)))
   (cond [(none? c)]
         [(= c "j") (setv sel (% (+ sel 1) (len playlist)))]
         [(= c "k") (setv sel (% (- sel 1) (len playlist)))]
         [(= c "J") (.playlist-skip lms server player)]
         [(= c "K") (.playlist-prev lms server player)]
         [(in c "p\n") (.playlist-play-index lms server player (get playlist sel "playlist index"))]
         [(= c "d") (.playlist-delete lms server player (get selected-track "playlist index"))]))))


(defn search-loop [scr server player player-name kind term]
 "Search the library to manipulate playlist."
 (global debug)
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
   (.search-results display scr player-name results term kind sel :debug debug)
   (setv selected-result (get results (% sel (len results))))
   (.refresh scr)
   (setv c (.getkey scr))
   (cond [(none? c)]
         [(in c "qh") (setv running False)]
         [(= c "r") (.clear scr)]
         [(= c "g") (setv sel 0)]
         [(= c "G") (setv sel (- (len playlist) 1))]
         [(= c "j") (setv sel (% (+ sel 1) (len results)))]
         [(= c "k") (setv sel (% (- sel 1) (len results)))]
         [(= c "D") (setv debug (not debug))]
         [(in c "aip\n") (.playlist-control lms server player
                          (get selected-result "id")
                          :action (cond [(= c "a") "add"]
                                        [(= c "i") "insert"]
                                        [:else "load"])
                          :kind control-kind)
                        (setv running False)]))))


(defn main [&kwonly server-ip port]
 "Main entry point.
 The command-line tool is in python because hy does not handle sigwinch, which
 breaks resizing in curses."
 (.wrapper curses server-loop :server-ip server-ip :port port))
 
