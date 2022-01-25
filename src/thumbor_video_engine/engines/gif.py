# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
# Copyright (c) 2015 Wikimedia Foundation

from thumbor.engines.gif import Engine as BaseEngine
try:
    from shutil import which
except ImportError:
    from thumbor.utils import which


class Engine(BaseEngine):

    def resize(self, width, height):
        width, height = int(width), int(height)
        super(Engine, self).resize(width, height)
        # Allow Gifsicle to add intermediate colors when resizing images.
        # Normally, Gifsicle's resize algorithms use input images' color
        # palettes without changes. When shrinking images with very few colors
        # (e.g., pure black-and-white images), adding intermediate colors can
        # improve the results. The following option allows Gifsicle to add
        # intermediate colors for images that have fewer than 64 input colors.
        self.operations.append("--resize-colors 64")

    def run_gifsicle(self, command):
        if not self.context.server.gifsicle_path:
            gifsicle_path = self.context.config.GIFSICLE_PATH or which('gifsicle')
            if not gifsicle_path:
                raise RuntimeError(
                    "gif engine was requested, but gifsicle binary cannot be found")
            self.context.server.gifsicle_path = gifsicle_path
        if self.context.config.GIFSICLE_ARGS:
            command += " %s" % " ".join(self.context.config.GIFSICLE_ARGS)
        return super(Engine, self).run_gifsicle(command)
