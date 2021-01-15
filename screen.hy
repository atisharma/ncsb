"""
A simple curses display class.
"""

(import os)
(import curses)
(import [curses [textpad]])
(import logging)


(defclass screen []
 """
 Manage the display.
 """

 (defn __init__ [self stdscr &kwonly [nodelay True] [halfdelay False]]
  (setv self.stdscr stdscr)
  (setv self.curses curses)
  (.curs_set curses False)
  (.nodelay stdscr nodelay)
  (when halfdelay (.halfdelay curses halfdelay))
  (.start_color curses)
  (.use_default_colors curses)
  (for [i (range 0 curses.COLORS)]
   (.init_pair curses (+ i 1) i -1))
  (setv self.window (.newwin curses curses.LINES curses.COLS))
  (self.clear)
  (setv self.warnings [])
  (setv self.errors [])
  (setv self.infos [])
  (setv self.debugs []))

 (defn __del__ [self]
  (.clear self.stdscr)
  (.curs_set curses True))

 (defn __enter__ [self]
  self)

 (defn __exit__ [self exc-type exc-val exc-tb])

 (defn clear [self]
  ;(.cbreak curses)
  ;(.noecho curses)
  (.clear self.stdscr)
  (.refresh self.stdscr)
  (.update_lines_cols curses)
  (.resize self.window curses.LINES curses.COLS)
  (setv self.warnings [])
  (setv self.errors [])
  (setv self.infos [])
  (setv self.debugs []))

 (defn clear_line [self y]
  (try
   (.addstr self.window y 0 " ")
   (.clrtoeol self.window)
   (except [curses.error])))

 (defn refresh [self]
  (.refresh self.window)
  (.erase self.window))

 (defn getkey [self]
  (try
   (.getkey self.stdscr)
   (except [curses.error] None)))

 (defn getch [self]
  (try
   (.getch self.stdscr)
   (except [curses.error] None)))

 (defn put [self y x s &kwonly [col 0] [style 0]]
     (setv (, h w) (.getmaxyx self.stdscr))
     (if (< y (- h 1))
         (try
          (.addnstr self.window y x f"{s}" (- w x) (| (.color_pair curses col) style))
          (except [curses.error]))))

 (defn input [self &optional [prompt ""]]
  """
  Get single-line input in a text box.
  """
  (setv y (- curses.LINES 2))
  (setv x (+ 4 (len prompt)))
  (.put self y 1 f"/{prompt}:" :col 191)
  (.refresh self.window)
  (setv tw (.newwin curses 1 (- curses.COLS 1) y x))
  (.bkgdset tw (| (.color_pair curses 191) curses.A_BOLD curses.A_ITALIC))
  (setv tb (.Textbox textpad tw :insert-mode True))
  (.edit tb (fn [x] (if (= x 10) 7 x)))
  (setv instr (-> tb (.gather) (.strip)))
  (.clear tw)
  (del tw)
  instr)

 (defn centre [self s]
  (setv (, y x) (.getmaxyx self.stdscr))
  (int (/ (- x (len s)) 2)))

 (defn right [self &kwonly [s " "]]
  (setv [y x] (.getmaxyx self.stdscr))
  (int (- x (len s) 1)))

 (defn bottom [self]
  (setv [y x] (.getmaxyx self.stdscr))
  (- y 2))

 (defn warning [self &rest strings]
  (for [s strings]
   (.append self.warnings s)))

 (defn error [self &rest strings]
  (for [s strings]
   (.append self.errors s)))

 (defn info [self &rest strings]
  (for [s strings]
   (.append self.infos s)))
 
 (defn debug[self &rest strings]
  (for [s strings]
   (.append self.debugs s)))

 (defn isEnabledFor [self x]
  (not (= x logging.DEBUG))))
