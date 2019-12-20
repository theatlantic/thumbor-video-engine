# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
# Copyright (c) 2015 Wikimedia Foundation

from thumbor.engines.gif import Engine as BaseEngine


class Engine(BaseEngine):

    def resize(self, width, height):
        super(Engine, self).resize(width, height)
        # Allow Gifsicle to add intermediate colors when resizing images.
        # Normally, Gifsicle's resize algorithms use input images' color
        # palettes without changes. When shrinking images with very few colors
        # (e.g., pure black-and-white images), adding intermediate colors can
        # improve the results. The following option allows Gifsicle to add
        # intermediate colors for images that have fewer than 64 input colors.
        self.operations.append("--resize-colors 64")
