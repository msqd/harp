Added
:::::

* Previous and next button in transaction detail pane allows to navigate through transactions (#394).
* Transaction list can be easily refreshed (#396).
* Transaction lists shows a summary of transaction count shown and total (#395).
* Stores storage metrics in prometheus gauges to monitor evolution.
* Adds a ``db:reset`` command to reset the database.
* Examples are now bundled within the ``harp.config.examples`` subpackage and can be loaded from commandline using
  ``-e name`` or ``--example name`` (#379).

Changed
:::::::

* Dashboard overview is now implemented using Apache ECharts and shows more information, in a clearer way.
