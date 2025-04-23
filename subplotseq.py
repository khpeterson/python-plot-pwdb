"""
SubplotSequence - A utility for creating interactive matplotlib figure
sequences.

This module provides a class for creating and navigating through a sequence of
matplotlib subplots using keyboard navigation. It's particularly useful for
presentations or interactive data exploration where you want to step through
multiple visualizations.

Navigation:
  - Right/Down arrow: Move to the next subplot in the sequence
  - Left/Up arrow: Move to the previous subplot in the sequence
"""

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy as np


class SubplotSequence:
    """
    A class for creating and navigating through a sequence of matplotlib
    subplots.

    This class allows you to add multiple matplotlib Axes objects to a sequence
    and then navigate through them using keyboard controls. Only one set of 
    axes is visible at a time. This is useful for presentations or data
    exploration.

    Attributes:
      figure: The matplotlib figure containing the subplots

    Example:
      >>> fig = plt.figure(figsize=(10, 6))
      >>> seq = SubplotSequence(fig)
      >>> ax1 = fig.add_subplot(121)
      >>> ax2 = fig.add_subplot(122)
      >>> seq.add(ax1)
      >>> seq.add(ax2)
      >>> seq.show()  # Navigate with arrow keys
    """

    def __init__(self, fig=None, **kwargs):
        """
        Initialize a new SubplotSequence.

        Args:
          fig: An existing matplotlib figure or None to create a new one
          **kwargs: Additional keyword arguments passed to plt.figure()
                   if fig is None
        """
        self.figure = fig if fig is not None else plt.figure(**kwargs)
        self._sequence = []  # List of axes or arrays of axes
        self._current = 0
        self._cid = None
        self._shown = False
        self._instruction_text = None
        self._navigation_text = "Use ← → arrow keys to navigate plots"

    def add(self, axes):
        """
        Add an Axes object or a numpy array/list of Axes to the sequence.

        Args:
          axes: A matplotlib Axes object, a list of Axes, or a numpy array
               of Axes

        Raises:
          TypeError: If axes is not a matplotlib Axes object, list, or numpy
                    array
        """
        # Accept single Axes, list of Axes, or numpy array of Axes
        if isinstance(axes, Axes):
            self._sequence.append([axes])
        elif isinstance(axes, (list, np.ndarray)):
            # Flatten if it's an array of axes
            axes_list = np.ravel(axes).tolist()
            self._sequence.append(axes_list)
        else:
            raise TypeError(
                "add() accepts a matplotlib Axes or an array/list of Axes."
            )

    def _set_visible(self, axes_list, visible: bool):
        """
        Set the visibility of a list of axes.

        Args:
          axes_list: List of matplotlib Axes objects
          visible: Boolean indicating whether axes should be visible
        """
        for ax in axes_list:
            ax.set_visible(visible)
        # Redraw canvas
        self.figure.canvas.draw_idle()

    def _add_navigation_text(self):
        """Add text with navigation instructions at the bottom of the figure."""
        if self._instruction_text is None:
            # Position at the bottom center of the figure
            self._instruction_text = self.figure.text(
                0.5, 0.01,  # x, y position (centered, bottom)
                self._navigation_text,
                ha='center',  # horizontally centered
                va='bottom',  # vertically aligned to bottom
                fontsize=9,
                color='gray',
                alpha=0.8,
                transform=self.figure.transFigure  # Use figure coordinates
            )

    def _update_navigation_text(self):
        """Update the navigation text to show current position in sequence."""
        if self._instruction_text is not None:
            position_info = f" ({self._current + 1}/{len(self._sequence)})"
            self._instruction_text.set_text(self._navigation_text + position_info)

    def _show_current(self):
        """
        Show only the current axes in the sequence and hide all others.
        """
        # Hide all axes
        for idx, axes_list in enumerate(self._sequence):
            self._set_visible(axes_list, idx == self._current)
        # Update navigation text with current position
        self._update_navigation_text()

    def _on_key(self, event):
        """
        Handle keyboard navigation events.

        Args:
          event: Matplotlib KeyEvent object
        """
        if event.key in ["right", "down"]:
            if self._current < len(self._sequence) - 1:
                self._current += 1
                self._show_current()
        elif event.key in ["left", "up"]:
            if self._current > 0:
                self._current -= 1
                self._show_current()

    def show(self):
        """
        Display the figure and enable keyboard navigation through the sequence.

        Shows the first set of axes in the sequence and sets up key bindings
        for navigation. Use arrow keys (left/right/up/down) to navigate.

        Raises:
          RuntimeError: If no axes have been added to the sequence
        """
        if not self._sequence:
            raise RuntimeError("No axes have been added to the sequence.")
        # Hide all axes except the first
        for idx, axes_list in enumerate(self._sequence):
            self._set_visible(axes_list, idx == 0)
        # Add navigation instructions
        self._add_navigation_text()
        self._update_navigation_text()
        # Connect key press event
        if self._cid is None:
            self._cid = self.figure.canvas.mpl_connect(
                'key_press_event', self._on_key
            )
        self._shown = True
        plt.show()
