"""
Various utility functions to handle data structures.
"""


(defn get-in [coll &rest args]
 "A get that returns None in case of missing keys."
 (if (and (isinstance coll dict) args (in (first args) coll))
  (get-in (get coll (first args)) #* (rest args))
  (if args None coll)))
