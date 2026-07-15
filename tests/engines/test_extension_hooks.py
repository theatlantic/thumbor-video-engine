import os

from thumbor_video_engine.engines.ffmpeg import Engine as FFmpegEngine


def load_gif(context, storage_path, name="hotdog.gif", **config):
    for k, v in config.items():
        setattr(context.config, k, v)
    with open(os.path.join(storage_path, name), mode="rb") as f:
        buf = f.read()
    engine = FFmpegEngine(context)
    engine.load(buf, ".gif")
    return engine, buf


def test_route_hook_labels_each_gifski_route(context, storage_path, mocker):
    routes = []

    class RecordingEngine(FFmpegEngine):
        def _gif_route(self, label, method, src_file, *args):
            routes.append(label)
            return super()._gif_route(label, method, src_file, *args)

    context.config.FFMPEG_GIF_PIPELINE = "gifski"
    engine = RecordingEngine(context)
    with open(os.path.join(storage_path, "hotdog.gif"), mode="rb") as f:
        engine.load(f.read(), ".gif")
    # don't actually shell out; just confirm the route is labelled
    mocker.patch.object(engine, "_gifski_y4m", return_value=b"gif")

    assert engine._transcode_to_gif_gifski("/tmp/x.gif") == b"gif"
    assert routes == ["y4m"]


def test_route_hook_used_for_legacy(context, storage_path, mocker):
    routes = []

    class RecordingEngine(FFmpegEngine):
        def _gif_route(self, label, method, src_file, *args):
            routes.append(label)
            return b"gif"

    engine = RecordingEngine(context)  # legacy is the default pipeline
    engine.extension = ".gif"
    assert engine.transcode_to_gif("/tmp/x.gif") == b"gif"
    assert routes == ["legacy"]


def test_oversized_target_hook(context, storage_path, mocker):
    class OversizedEngine(FFmpegEngine):
        def _gifski_oversized_target(self, src_file):
            return b"fast-first"

    context.config.FFMPEG_GIF_PIPELINE = "gifski"
    context.config.GIFSKI_MAX_TARGET_PIXELS = 1  # everything is "oversized"
    with open(os.path.join(storage_path, "hotdog.gif"), mode="rb") as f:
        engine = OversizedEngine(context)
        engine.load(f.read(), ".gif")

    assert engine._transcode_to_gif_gifski("/tmp/x.gif") == b"fast-first"


def test_gifski_quality_and_extra_args_hooks(context):
    class FastEngine(FFmpegEngine):
        def _gifski_path(self):
            return "/usr/bin/gifski"

        def _gifski_quality(self):
            return 40

        def _gifski_extra_args(self):
            return ["--fast"]

    engine = FastEngine(context)
    engine.image_size = (100, 75)
    cmd = engine._gifski_cmd("/tmp/out.gif", 25)

    assert "--fast" in cmd
    assert cmd[cmd.index("--quality") + 1] == "40"
    assert cmd[cmd.index("--width") + 1] == "100"


def test_gifski_quality_default(context):
    context.config.GIFSKI_QUALITY = 90
    engine = FFmpegEngine(context)
    assert engine._gifski_quality() == 90
    assert engine._gifski_extra_args() == []


def test_gifski_gifsicle_pass_hook_gates_the_pass(context, storage_path, mocker):
    # a subclass can suppress the gifsicle -O3 pass per request even when
    # GIFSKI_GIFSICLE_PASS is configured on
    class NoPassEngine(FFmpegEngine):
        def _gifski_gifsicle_pass(self):
            return False

    context.config.FFMPEG_GIF_PIPELINE = "gifski"
    context.config.GIFSKI_GIFSICLE_PASS = True
    with open(os.path.join(storage_path, "hotdog.gif"), mode="rb") as f:
        engine = NoPassEngine(context)
        engine.load(f.read(), ".gif")
    engine.resize(100, 75)
    gifsicle_spy = mocker.spy(NoPassEngine, "_gifsicle_optimize_file")

    engine.read(".gif", quality=80)
    assert gifsicle_spy.call_count == 0


def test_gifski_gifsicle_pass_default_follows_config(context):
    context.config.GIFSKI_GIFSICLE_PASS = True
    assert FFmpegEngine(context)._gifski_gifsicle_pass() is True
    context.config.GIFSKI_GIFSICLE_PASS = False
    assert FFmpegEngine(context)._gifski_gifsicle_pass() is False
