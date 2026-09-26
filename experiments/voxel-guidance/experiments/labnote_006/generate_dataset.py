# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic Blender synthetic observation and ray-depth generator."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from dataset_contract import FORMAT, VERSION, SPLIT_RANGES, canonical_json, sha256_file  # noqa: E402

OBSERVATION_SIZE = 64
TARGET_SIZE = 16
FRAMES = 4
MAX_DEPTH = 20.0


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=sorted(SPLIT_RANGES), required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--sequences", type=int, required=True)
    marker = sys.argv.index("--") + 1 if "--" in sys.argv else len(sys.argv)
    return parser.parse_args(sys.argv[marker:])


def material(name: str, value: float):
    item = bpy.data.materials.new(name)
    item.diffuse_color = (value, value, value, 1.0)
    item.roughness = 1.0
    return item


def cube(name: str, location, scale, gray: float):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    item = bpy.context.object
    item.name = name
    item.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    item.data.materials.append(material(f"{name}-material", gray))
    return item


def build_scene(seed: int):
    rng = random.Random(seed)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

    floor_gray = rng.uniform(0.18, 0.72)
    cube("floor", (0, 2, -0.15), (8, 10, 0.15), floor_gray)
    cube("back-wall", (0, 11.5, 2.0), (8, 0.15, 2.15), rng.uniform(0.2, 0.8))
    cube("left-wall", (-7.85, 2, 1.5), (0.15, 10, 1.65), rng.uniform(0.2, 0.8))
    cube("right-wall", (7.85, 2, 1.5), (0.15, 10, 1.65), rng.uniform(0.2, 0.8))

    for index in range(rng.randint(8, 18)):
        width, depth, height = rng.uniform(0.35, 1.6), rng.uniform(0.35, 1.6), rng.uniform(0.3, 3.0)
        x, y = rng.uniform(-6.2, 6.2), rng.uniform(-3.0, 10.0)
        cube(f"obstacle-{index}", (x, y, height / 2), (width, depth, height / 2), rng.uniform(0.08, 0.92))

    # Raised shelves and overhead occluders create depth discontinuities without
    # assuming a game-specific semantic class.
    for index in range(rng.randint(2, 5)):
        x, y = rng.uniform(-5.5, 5.5), rng.uniform(0.0, 9.0)
        cube(f"shelf-{index}", (x, y, rng.uniform(1.0, 2.5)),
             (rng.uniform(0.8, 2.0), rng.uniform(0.3, 0.8), rng.uniform(0.08, 0.2)), rng.uniform(0.12, 0.88))

    world = bpy.context.scene.world or bpy.data.worlds.new("world")
    bpy.context.scene.world = world
    world.color = (rng.uniform(0.01, 0.12),) * 3
    bpy.ops.object.light_add(type="AREA", location=(rng.uniform(-4, 4), rng.uniform(-1, 7), rng.uniform(5, 9)))
    light = bpy.context.object
    light.data.energy = rng.uniform(500, 1800)
    light.data.shape = "DISK"
    light.data.size = rng.uniform(3, 8)

    bpy.ops.object.camera_add(location=(0, -5, 1.6))
    camera = bpy.context.object
    camera.data.lens = rng.uniform(24, 48)
    camera.data.sensor_width = 36
    bpy.context.scene.camera = camera
    return rng, camera


def look(camera, yaw: float, pitch: float):
    direction = Vector((math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_gray(scene, temporary_path: Path) -> np.ndarray:
    scene.render.filepath = str(temporary_path)
    bpy.ops.render.render(write_still=True)
    rendered = bpy.data.images.load(str(temporary_path), check_existing=False)
    pixels = np.asarray(rendered.pixels[:], dtype=np.float32)
    rgba = pixels.reshape(OBSERVATION_SIZE, OBSERVATION_SIZE, 4)
    rgb = np.flipud(rgba[:, :, :3])
    gray = rgb @ np.asarray([0.2126, 0.7152, 0.0722], dtype=np.float32)
    bpy.data.images.remove(rendered)
    temporary_path.unlink()
    return np.clip(np.rint(gray * 255), 0, 255).astype(np.uint8)


def ray_depth(scene, camera) -> np.ndarray:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    frame = camera.data.view_frame(scene=scene)
    top_left, top_right, bottom_right, bottom_left = frame[3], frame[0], frame[1], frame[2]
    origin = camera.matrix_world.translation
    result = np.full((TARGET_SIZE, TARGET_SIZE), MAX_DEPTH, dtype=np.float32)
    for row in range(TARGET_SIZE):
        v = (row + 0.5) / TARGET_SIZE
        left = top_left.lerp(bottom_left, v)
        right = top_right.lerp(bottom_right, v)
        for column in range(TARGET_SIZE):
            u = (column + 0.5) / TARGET_SIZE
            point = left.lerp(right, u)
            direction = (camera.matrix_world.to_quaternion() @ point).normalized()
            hit, location, _normal, _face, _obj, _matrix = scene.ray_cast(depsgraph, origin, direction, distance=MAX_DEPTH)
            if hit:
                result[row, column] = min(MAX_DEPTH, (location - origin).length)
    return result


def discontinuities(depth: np.ndarray) -> np.ndarray:
    edge = np.zeros_like(depth, dtype=np.uint8)
    edge[:, 1:] |= (np.abs(depth[:, 1:] - depth[:, :-1]) > 1.0)
    edge[1:, :] |= (np.abs(depth[1:, :] - depth[:-1, :]) > 1.0)
    return edge


def configure_render(scene):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = OBSERVATION_SIZE
    scene.render.resolution_y = OBSERVATION_SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"


def generate_sequence(seed: int, path: Path):
    rng, camera = build_scene(seed)
    scene = bpy.context.scene
    configure_render(scene)
    start_x = rng.uniform(-2.5, 2.5)
    start_y = rng.uniform(-6.0, -3.5)
    yaw0 = rng.uniform(-0.35, 0.35)
    velocity = rng.uniform(0.18, 0.5)
    yaw_rate = rng.uniform(-0.07, 0.07)
    pitch = rng.uniform(-0.16, 0.04)
    images, depths, edges, ego = [], [], [], []
    previous = None
    for frame in range(FRAMES):
        yaw = yaw0 + frame * yaw_rate
        position = Vector((start_x + math.sin(yaw0) * velocity * frame,
                           start_y + math.cos(yaw0) * velocity * frame,
                           1.6 + 0.03 * math.sin(frame)))
        camera.location = position
        look(camera, yaw, pitch)
        images.append(render_gray(scene, path.with_suffix(f".frame-{frame}.png")))
        depth = ray_depth(scene, camera)
        depths.append(depth)
        edges.append(discontinuities(depth))
        if previous is None:
            ego.append((0.0, 0.0, 0.0))
        else:
            delta = position - previous[0]
            ego.append((float(delta.x), float(delta.y), float(yaw - previous[1])))
        previous = (position.copy(), yaw)
    np.savez_compressed(path, image=np.stack(images), depth=np.stack(depths),
                        edge=np.stack(edges), ego=np.asarray(ego, dtype=np.float32),
                        scene_seed=np.asarray(seed, dtype=np.int64))


def main():
    args = arguments()
    allowed = SPLIT_RANGES[args.split]
    seeds = list(range(args.seed_start, args.seed_start + args.sequences))
    if args.sequences < 1 or any(seed not in allowed for seed in seeds):
        raise SystemExit("requested seeds fall outside the registered split range")
    args.output.mkdir(parents=True, exist_ok=True)
    shards = []
    for index, seed in enumerate(seeds, 1):
        path = args.output / f"scene-{seed:05d}.npz"
        generate_sequence(seed, path)
        shards.append({"path": path.name, "scene_seed": seed, "sha256": sha256_file(path), "bytes": path.stat().st_size})
        print(f"generated {index}/{len(seeds)} seed={seed}", flush=True)
    manifest = {
        "format": FORMAT, "version": VERSION, "split": args.split,
        "generator": {"blender": bpy.app.version_string, "observation_size": OBSERVATION_SIZE,
                      "target_size": TARGET_SIZE, "frames": FRAMES, "maximum_depth_m": MAX_DEPTH},
        "shards": shards,
    }
    (args.output / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "split": args.split, "shards": len(shards)}))


if __name__ == "__main__":
    main()
