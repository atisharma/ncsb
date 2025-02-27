"
Control LMS by the json RPC interface.

LMS API documentation is at
http://lms-vm:9000/html/doc/cli-api.html
https://github.com/elParaguayo/LMS-CLI-Documentation/blob/master/LMS-CLI.md
"

(require hyrule.argmove [-> ->> as->])
(require hyrule.control [unless])

(import requests)
(import shutil)
(import pathlib [Path])

(import ncsb.util [first second rest get-in none? inc dec remove tempdir])

(defclass LMSError [Exception])


(defclass Server []
  "Context manager for LMS connection."

  (defn __init__ [self server [port 9000]]
    (setv self.url f"http://{server}:{port}/jsonrpc.js")
    (setv self.ip server)
    (setv self.port port)
    (.mkdir (Path "{tempdir}") :parents True :exist-ok True))

  (defn __del__ [self])

  (defn __enter__ [self]
    self)

  (defn __exit__ [self exc-type exc-val exc-tb]
    (.rmtree shutil "{tempdir}" :ignore-errors True))

  (defn send [self command]
    "Send a command list to the LMS server.
    These are nested lists of format
    [player-id [cmd1 arg1 arg2...]].
    The player id is the mac address or - for the server."
    (setv payload {"method" "slim.request" "params" command})
    (try
      (-> (.post requests self.url :json payload)
        (.json)
        (get "result"))
      (except [e [requests.exceptions.RequestException]]
        (raise (LMSError (str e))))))

  (defn coverart [self coverid [h 200] [w 200] * [fname None]]
    "Fetch the cover art from the LMS server.
    Save to fname or {tempdir}/{coverid}.png."
    (setv url f"http://{self.ip}:{self.port}/music/{coverid}/cover_{h}x{w}.png")
    (try
      (with [r (.get requests url :stream True)]
        (with [f (open (or fname f"{tempdir}/{coverid}.png") "wb")]
          (.copyfileobj shutil r.raw f)))
      (except [e [requests.exceptions.RequestException FileNotFoundError]]
        (raise (LMSError (str e))))))

  ;; In addition, there is a shortcut URL to return the artwork of the currently playing song for a player:
  ;;    http://<server>:<port>/music/<wbr>current/cover.jpg?player=<<wbr>playerid>)))

  (defn remote-coverart [self url * [fname None]]
    "Fetch remote cover art from a provided LMS server.
    Save to fname or {tempdir}/remote.png."
    ;; If not http in url, it's a local url which needs expanding.
    (unless (in "http" url) (setv url f"http://{self.ip}:{self.port}/{url}"))
    (try
      (with [r (.get requests url :stream True)]
        (with [f (open (or fname f"{tempdir}/remote.png") "wb")]
          (.copyfileobj shutil r.raw f)))
      (except [e [requests.exceptions.RequestException FileNotFoundError]]
        (raise (LMSError (str e)))))))


(defn player-count [server]
  "Return number of players."
  (.send server ["-" ["player" "count" "?"]]))

(defn players [server]
  "Return a list of player dicts."
  (as-> server x
    (player-count x)
    (.send server ["-" ["players" "0" x]])
    (get-in x "players_loop")))

(defn rescan-progress [server]
  "Return progress of a rescan."
  (get-in (.send server ["-" ["rescanprogress"]]) "rescan"))

(defn version [server]
  "Return LMS version number."
  (get-in (.send server ["-" ["version" "?"]]) "_version"))

(defn serverstatus [server]
  "Return LMS server status."
  (.send server ["-" ["serverstatus"]]))


(defn status [server mac * [from 0] [to 50]]
  "Return detailed status of a player's playlist."
  (.send server [mac ["status" from to "tags:a,l,c,d,e,s,t,j,J,K,L,x,N,r,o"]]))

(defn mode [server mac]
  "Return player mode."
  (get-in (.send server [mac ["mode" "?"]]) "_mode"))

(defn wifi [server mac]
  "Return player's wifi signal strength."
  (get-in (.send server [mac ["signalstrength" "?"]]) "_signalstrength"))

(defn model [server mac]
  "Return player model."
  (get-in (.send server [mac ["player" "model" "?"]]) "_model"))

(defn ip [server mac]
  "Return player ip."
  (get-in (.send server [mac ["player" "ip" "?"]]) "_ip"))

(defn power [server mac [action "?"]]
  "Set (1|0)/toggle (toggle)/query (?) power status of player."
  (cond (= action "toggle") (power server mac (not (int (power server mac))))
        :else (get-in (.send server [mac ["power" action]]) "_power")))

(defn play [server mac]
  "Start the player."
  (.send server [mac ["play"]]))

(defn stop [server mac]
  "Stop the player."
  (.send server [mac ["stop"]]))

(defn pause [server mac]
  "Toggle the pause/play status of the player."
  (.send server [mac ["pause"]]))

(defn seek-forward [server mac]
  "Seek some seconds forward in the current song."
  (.send server [mac ["time" "+5"]]))

(defn seek-backward [server mac]
  "Seek some seconds backwards in the current song."
  (.send server [mac ["time" "-5"]]))

(defn artist [server mac]
  "Return track artist of current playlist item."
  (or (get-in (.send server [mac ["artist" "?"]]) "_artist") ""))

(defn album [server mac]
  "Return track album of current playlist item."
  (or (get-in (.send server [mac ["album" "?"]]) "_album") ""))

(defn title [server mac]
  "Return track title of current playlist item."
  (or (get-in (.send server [mac ["title" "?"]]) "_title") ""))

(defn track-duration [server mac]
  "Return track duration (in s) of current playlist item."
  (get-in (.send server [mac ["duration" "?"]]) "_duration"))

(defn track-elapsed [server mac]
  "Return track time elapsed (in s) of current playlist item."
  (get-in (.send server [mac ["time" "?"]]) "_time"))

(defn track-remaining [server mac]
  "Return track time remaining (in s) of current playlist item."
  (- (track-duration server mac) (track-elapsed server mac)))

(defn track-elapsed-fraction [server mac]
  "Return track elapsed (as a fraction) of current playlist item."
  (setv elapsed (track-elapsed server mac))
  (setv duration (track-duration server mac))
  (if (or (isinstance elapsed str) (isinstance duration str))
    0
    (/ elapsed duration)))


(defn volume [server mac volume]
  "Set the volume of the player (between 0 and 100)."
  (.send server [mac ["mixer" "volume" f"{(-> volume int (min 100) (max 0))}"]]))

(defn volume-change [server mac change]
  "Increase the volume of the player by change."
  (.send server [mac ["mixer" "volume" f"{(int change) :+d}"]]))


(defn track-count [server mac]
  "Return number of tracks in current playlist."
  (get-in (.send server [mac ["playlist" "tracks" "?"]]) "_tracks"))

(defn playlist-skip [server mac]
  "Play next item in playlist."
  (playlist-play-index server mac
                       (-> (playlist-position server mac)
                         (int)
                         (+ 1))))

(defn playlist-prev [server mac]
  "Play previous item in playlist."
  (playlist-play-index server mac
                       (-> (playlist-position server mac)
                         (int)
                         (- 1)
                         (max 0))))

(defn playlist-jump [server mac n]
  "Jump to index n in the playlist."
  (.send server [mac ["playlist" "jump" n]]))

(defn playlist-move [server mac from to]
  "Move track #from to #to in the playlist."
  (.send server [mac ["playlist" "move" from to]]))

(defn playlist-move-up [server mac n]
  "Move track n in the playlist to one before."
  (playlist-move server mac n (max 0 (dec n))))

(defn playlist-move-down [server mac n]
  "Move track n in the playlist to one later."
  (playlist-move server mac n (inc n)))

(defn playlist-play-index [server mac n]
  "Play nth item in playlist."
  (.send server [mac ["playlist" "index" f"{(int n)}"]]))

(defn playlist-clear [server mac]
  "Clear current playlist."
  (.send server [mac ["playlist" "clear"]]))

(defn playlist-delete [server mac index]
  "Delete by index from playlist."
  (.send server [mac ["playlist" "delete" f"{index :d}"]]))

(defn playlist-position [server mac]
  "Return index of current item in playlist."
  (get-in (.send server [mac ["playlist" "index" "?"]]) "_index"))

(defn playlist-shuffle [server mac [kind "?"]]
  "Shuffle (0 off|1 songs|2 albums|?)"
  (.send server [mac ["playlist" "shuffle" kind]]))

(defn playlist-repeat [server mac [kind "0"]]
  "Repeat (0 off|1 song|2 playlist)"
  (.send server [mac ["playlist" "repeat" kind]]))

(defn playlist-control [server mac item * [action "load"] [kind "track"]]
  "Play (load), insert or add an item to a playlist where item is the id
  and kind is one of album, artist or track."
  (.send server [mac ["playlistcontrol" f"cmd:{action}" f"{kind}_id:{item}"]]))


(defn search-on-artist [server artist]
  "Get albums by artist."
  (search server mac "albums" artist))

(defn search-on-album [server album]
  "Get tracks on album."
  (search server mac "songs" album))

(defn search [server mac kind params]
  "Search on a general term.
  kind is one of artists, albums, songs, tracks, playlists."
  (.send server [mac [kind 0 100 params]]))

(defn songinfo [server track_id]
  "Return all information on a song."
  (.send server ["-" ["songinfo" 0 200 f"track_id:{track_id}"]]))

(defn browse [server folder-id * [return-top True] [tags "o"]]
  "Browse a music library folder."
  (get-in (if return-top
            (.send server ["-" ["musicfolder" 0 200 f"folder_id:{folder_id}" f"tags:{tags}"]])
            (.send server ["-" ["musicfolder" 0 200 f"folder_id:{folder_id}" f"tags:{tags}" "return_top:1"]]))
          "folder_loop"))
