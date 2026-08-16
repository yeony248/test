"""장면 PNG들을 ffmpeg로 세로 영상 한 편으로 렌더링."""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

from . import config
from .scenes import Scene

AUDIO_EXT = (".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac")


class RenderError(RuntimeError):
    pass


def find_bgm(bgm_dir: str | Path | None) -> list[Path]:
    if not bgm_dir:
        return []
    path = Path(bgm_dir)
    if not path.exists():
        return []
    return sorted(p for p in path.iterdir()
                  if p.is_file() and p.suffix.lower() in AUDIO_EXT)


# 줌/팬이 셀수록 화면 가장자리가 많이 잘린다. 이 값은 scenes.py의 SIDE_MARGIN과
# 짝을 이룬다 — 여기를 키우면 글자가 잘릴 수 있으니 여백도 같이 키울 것.
MAX_ZOOM = 1.10
ZOOM_RATE = 0.0011  # 프레임당 배율 증가폭
PAN_RANGE = (0.2, 0.8)  # 팬은 이동 가능 범위의 가운데 60%만 쓴다


def _zoompan(motion: str, frames: int, w: int, h: int, fps: int) -> str:
    """켄번스(느린 줌/팬) 필터. 큰 해상도로 키운 뒤 잘라내야 떨림이 없다."""
    if motion == "none":
        return f"scale={w}:{h}"

    big = f"scale={w * 2}:{h * 2}"
    lo, hi = PAN_RANGE
    span = f"({lo}+{hi - lo:.3f}*on/{frames})"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"

    if motion == "in":
        z = f"min(1.0+{ZOOM_RATE}*on,{MAX_ZOOM})"
        x, y = cx, cy
    elif motion == "out":
        z = f"max({MAX_ZOOM}-{ZOOM_RATE}*on,1.0)"
        x, y = cx, cy
    elif motion == "left":
        z = str(MAX_ZOOM)
        x, y = f"(iw-iw/zoom)*{span}", cy
    elif motion == "right":
        z = str(MAX_ZOOM)
        x, y = f"(iw-iw/zoom)*({lo + hi}-{span})", cy
    else:  # up
        z = str(MAX_ZOOM)
        x, y = cx, f"(ih-ih/zoom)*{span}"

    return f"{big},zoompan=z='{z}':x='{x}':y='{y}':d=1:s={w}x{h}:fps={fps}"


def build_command(scenes: list[Scene], out_path: Path,
                  settings: config.RenderSettings,
                  bgm: Path | None = None,
                  bgm_offset: float = 0.0,
                  transitions: list[str] | None = None) -> tuple[list[str], float]:
    """ffmpeg 인자 리스트와 최종 영상 길이(초)를 만든다."""
    if not scenes:
        raise RenderError("장면이 없습니다.")
    for scene in scenes:
        if scene.path is None:
            raise RenderError("장면 PNG가 저장되지 않았습니다. save_scenes()를 먼저 부르세요.")

    w, h, fps = settings.width, settings.height, settings.fps
    xf = settings.xfade if len(scenes) > 1 else 0.0
    total = sum(s.duration for s in scenes) - xf * (len(scenes) - 1)

    cmd = [config.ffmpeg_bin(), "-y", "-nostdin", "-loglevel", "error"]
    for scene in scenes:
        cmd += ["-loop", "1", "-framerate", str(fps),
                "-t", f"{scene.duration:.3f}", "-i", str(scene.path)]

    audio_index = len(scenes)
    if bgm is not None:
        cmd += ["-stream_loop", "-1", "-ss", f"{bgm_offset:.2f}", "-i", str(bgm)]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

    parts: list[str] = []
    for i, scene in enumerate(scenes):
        frames = max(1, round(scene.duration * fps))
        parts.append(
            f"[{i}:v]{_zoompan(scene.motion, frames, w, h, fps)},"
            f"setsar=1,format=yuv420p[v{i}]"
        )

    if len(scenes) == 1:
        last = "v0"
    else:
        picks = transitions or ["fade"] * (len(scenes) - 1)
        last = "v0"
        offset = scenes[0].duration - xf
        for i in range(1, len(scenes)):
            label = f"x{i}"
            parts.append(
                f"[{last}][v{i}]xfade=transition={picks[i - 1]}:"
                f"duration={xf:.3f}:offset={offset:.3f}[{label}]"
            )
            last = label
            offset += scenes[i].duration - xf

    fade_out_at = max(0.0, total - 1.0)
    parts.append(
        f"[{audio_index}:a]volume={settings.bgm_volume},"
        f"afade=t=in:st=0:d=0.8,"
        f"afade=t=out:st={fade_out_at:.3f}:d=1.0,"
        f"asetpts=PTS-STARTPTS[aout]"
    )

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", f"[{last}]", "-map", "[aout]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", settings.preset, "-crf", str(settings.crf),
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart",
        str(out_path),
    ]
    return cmd, total


def render(scenes: list[Scene], out_path: Path, settings: config.RenderSettings,
           bgm: Path | None = None, rng: random.Random | None = None,
           transitions: list[str] | None = None) -> float:
    rng = rng or random.Random()
    offset = round(rng.uniform(0, 25), 2) if bgm else 0.0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd, total = build_command(scenes, out_path, settings, bgm, offset, transitions)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RenderError(
            f"ffmpeg 실패 (exit {proc.returncode})\n{proc.stderr.strip()[-1500:]}"
        )
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RenderError(f"영상 파일이 만들어지지 않았습니다: {out_path}")
    return total
