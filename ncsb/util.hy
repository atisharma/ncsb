"""
Various utility functions to handle data structures.
"""

(import hyrule [inc dec rest butlast starmap distinct])
(import itertools [repeat filterfalse :as remove])

(import tempfile)


(setv tempdir (.join "/" [(tempfile.gettempdir) "ncsb"]))

(defn none? [x]
  (is x None))

(defn first [xs]
  (get (list xs) 0))

(defn second [xs]
  (get (list xs) 1))

(defn get-in [coll #* args]
  "A get that returns None in case of missing keys."
  (if (and (isinstance coll dict) args (in (first args) coll))
      (get-in (get coll (first args)) #* (rest args))
      (if args None coll)))
