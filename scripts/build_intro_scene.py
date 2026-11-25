"""Build the Steam Archive intro film in Blender.

Run:
  blender.exe -b --factory-startup --python scripts/build_intro_scene.py -- --test
  blender.exe -b --factory-startup --python scripts/build_intro_scene.py

The final render is intentionally a short, silent fly-through:
four archive gates, game totems, then a monumental STEAM reveal.
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "renders", "intro")
TAU = math.pi * 2
TEST = "--test" in sys.argv

FPS = 24
FRAME_END = 192

CYAN = (0.18, 0.66, 1.0)
AMBER = (1.0, 0.58, 0.16)
PURPLE = (0.55, 0.34, 1.0)
MINT = (0.16, 0.9, 0.72)
WHITE = (0.82, 0.92, 1.0)
DARK = (0.006, 0.012, 0.025)


# ---------------------------------------------------------------------------
# scene helpers
# ---------------------------------------------------------------------------

def reset():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def collection(name):
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def move_to(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def emission(name, color, strength=5.0):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1)
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def metal(name, color, metallic=0.75, roughness=0.28, glow=None, strength=0.0):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if glow:
        bsdf.inputs["Emission Color"].default_value = (*glow, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def apply(obj, mat):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)
    return obj


def smooth(obj):
    if obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def bevel(obj, width=0.06, segments=2):
    mod = obj.modifiers.new("soft edge", "BEVEL")
    mod.width = width
    mod.segments = segments
    return obj


def cube(name, loc, scale, mat, coll, rot=(0, 0, 0), soft=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply(obj, mat)
    if soft:
        bevel(obj, soft)
    return move_to(obj, coll)


def sphere(name, loc, radius, mat, coll, segments=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    apply(obj, mat)
    smooth(obj)
    return move_to(obj, coll)


def torus(name, loc, major, minor, mat, coll, rot=(math.radians(90), 0, 0), seg=96, ring=8):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major,
        minor_radius=minor,
        major_segments=seg,
        minor_segments=ring,
        location=loc,
        rotation=rot,
    )
    obj = bpy.context.object
    obj.name = name
    apply(obj, mat)
    smooth(obj)
    return move_to(obj, coll)


def curve_ring(name, loc, radius, bevel, mat, coll, rot=(math.radians(90), 0, 0), seg=128):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(seg - 1)
    for i, point in enumerate(spline.points):
        angle = TAU * i / seg
        point.co = (math.cos(angle) * radius, math.sin(angle) * radius, 0.0, 1.0)
    obj = bpy.data.objects.new(name, curve)
    obj.location = loc
    obj.rotation_euler = rot
    coll.objects.link(obj)
    apply(obj, mat)
    return obj


def text(name, body, loc, size, mat, coll, align="CENTER", extrude=0.02, rot=(math.radians(90), 0, 0)):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = align
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = extrude
    obj.data.bevel_depth = 0.008
    obj.data.bevel_resolution = 1
    apply(obj, mat)
    return move_to(obj, coll)


def key_location(obj, frame, loc):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def key_rotation(obj, frame, rot):
    obj.rotation_euler = rot
    obj.keyframe_insert("rotation_euler", frame=frame)


def key_scale(obj, frame, scale):
    obj.scale = scale
    obj.keyframe_insert("scale", frame=frame)


def point_light(name, loc, color, energy, radius=8, coll=None):
    data = bpy.data.lights.new(name, "POINT")
    data.color = color
    data.energy = energy
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    (coll or bpy.context.scene.collection).objects.link(obj)
    obj.location = loc
    return obj


# ---------------------------------------------------------------------------
# world
# ---------------------------------------------------------------------------

def build_world():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_END

    world = bpy.data.worlds.new("Steam archive void")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*DARK, 1)
    bg.inputs["Strength"].default_value = 0.35
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # subtle mist glow near the floor
    # NOTE: no literal floor plane; a finite plane creates a hard horizon line
    # in a fly-through. The void and the gate glow carry the depth instead.


def build_stars():
    coll = collection("STARS")
    mat = emission("star dust", (0.55, 0.82, 1.0), 2.2)
    random.seed(8)
    parts = []
    for i in range(260):
        x = random.uniform(-26, 26)
        y = random.uniform(-18, 96)
        z = random.uniform(-8, 28)
        r = random.uniform(0.018, 0.085)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=(x, y, z))
        part = bpy.context.object
        part.name = "star"
        apply(part, mat)
        parts.append(part)
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    stars = bpy.context.object
    stars.name = "star field"
    move_to(stars, coll)
    key_rotation(stars, 1, (0, 0, 0))
    key_rotation(stars, FRAME_END, (0.08, 0, 0.18))
    return stars


def build_dust():
    coll = collection("DUST")
    mat = emission("dust streak", (0.2, 0.55, 0.86), 1.0)
    random.seed(13)
    parts = []
    for i in range(44):
        x = random.uniform(-17, 17)
        y = random.uniform(-8, 86)
        z = random.uniform(-5, 16)
        length = random.uniform(0.5, 3.4)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
        part = bpy.context.object
        part.name = "dust"
        part.scale = (random.uniform(0.015, 0.04), length, random.uniform(0.015, 0.04))
        apply(part, mat)
        parts.append(part)
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    dust = bpy.context.object
    dust.name = "dust field"
    move_to(dust, coll)
    return dust


def build_gate(index, y, radius, color):
    coll = collection("GATES")
    gate = bpy.data.objects.new("gate %02d" % index, None)
    coll.objects.link(gate)
    gate.location = (0, y, 0)

    ring_mat = emission("gate %02d glow" % index, color, 4.2)
    faint = emission("gate %02d faint" % index, color, 1.25)

    ring = torus("gate %02d outer" % index, (0, 0, 0), radius, 0.12, ring_mat, coll, seg=128)
    ring.parent = gate
    inner = torus("gate %02d inner" % index, (0, 0, 0), radius * 0.79, 0.045, faint, coll, seg=128)
    inner.parent = gate

    for i in range(12):
        angle = TAU * i / 12
        seg = cube(
            "gate %02d tick %02d" % (index, i),
            (math.cos(angle) * radius, 0, math.sin(angle) * radius),
            (radius * 0.085, 0.035, 0.035),
            ring_mat,
            coll,
            rot=(0, -angle, 0),
            soft=0,
        )
        seg.parent = gate

    # tiny satellites orbit the gate in depth
    for i in range(4):
        angle = TAU * i / 4 + 0.3
        sat = cube(
            "gate %02d satellite %02d" % (index, i),
            (math.cos(angle) * (radius + 1.4), -0.9, math.sin(angle) * (radius + 1.4)),
            (0.06, 0.06, 0.06),
            ring_mat,
            coll,
            soft=0,
        )
        sat.parent = gate

    # Gate labels were intentionally removed: aligned rings made every label
    # stack on top of the previous one. The category cards carry the words.

    point_light("gate %02d light" % index, (0, y + 0.5, 4), color, 800, radius=9)

    key_rotation(gate, 1, (0, 0, 0))
    key_rotation(gate, FRAME_END, (0, math.radians(16 + index * 3), 0))
    key_scale(gate, 1, (1, 1, 1))
    key_scale(gate, 24, (1.035, 1.035, 1.035))
    key_scale(gate, 48, (1, 1, 1))
    key_scale(gate, 96, (1.025, 1.025, 1.025))
    key_scale(gate, 144, (1, 1, 1))
    return gate


# ---------------------------------------------------------------------------
# game totems
# ---------------------------------------------------------------------------

def build_dice(loc):
    coll = collection("TOTEMS")
    root = bpy.data.objects.new("dice", None)
    coll.objects.link(root)
    root.location = loc
    body = cube("dice body", (0, 0, 0), (0.78, 0.78, 0.78), metal("dice shell", (0.02, 0.08, 0.12), .55, .25, (0.1, 0.6, 0.9), 0.6), coll, soft=0.12)
    body.parent = root
    pips = emission("dice pips", (0.42, 0.95, 1.0), 5.0)
    positions = [(-0.24, -0.4, 0.24), (0.24, -0.4, 0.24), (0, -0.4, 0), (-0.24, -0.4, -0.24), (0.24, -0.4, -0.24)]
    for i, p in enumerate(positions):
        pip = sphere("dice pip %d" % i, p, 0.055, pips, coll, segments=12, rings=6)
        pip.parent = root
    key_rotation(root, 1, (0.1, 0.2, -0.15))
    key_rotation(root, FRAME_END, (0.7, 1.4, 0.8))
    return root


def build_sword(loc):
    coll = collection("TOTEMS")
    root = bpy.data.objects.new("sword", None)
    coll.objects.link(root)
    root.location = loc
    steel = metal("sword steel", (0.3, 0.55, 0.7), .9, .2, (0.32, 0.82, 1.0), 1.8)
    gold = emission("sword gold", AMBER, 4.0)
    blade = cube("sword blade", (0, 0, 1.1), (0.13, 0.04, 1.25), steel, coll, soft=0.03)
    blade.parent = root
    tip = cube("sword tip", (0, 0, 2.45), (0.09, 0.04, 0.32), steel, coll, rot=(0, math.radians(45), 0), soft=0.02)
    tip.parent = root
    guard = cube("sword guard", (0, 0, -0.12), (0.62, 0.06, 0.09), gold, coll, soft=0.04)
    guard.parent = root
    grip = cube("sword grip", (0, 0, -0.58), (0.08, 0.07, 0.42), metal("sword grip mat", (0.06, 0.03, 0.02), .2, .55), coll)
    grip.parent = root
    pommel = sphere("sword pommel", (0, 0, -0.84), 0.16, gold, coll)
    pommel.parent = root
    key_rotation(root, 1, (0, 0, -0.18))
    key_rotation(root, FRAME_END, (0.05, 0, 0.38))
    return root


def build_wheel(loc):
    coll = collection("TOTEMS")
    root = bpy.data.objects.new("wheel", None)
    coll.objects.link(root)
    root.location = loc
    rim = emission("wheel rim", AMBER, 3.8)
    hub_mat = metal("wheel hub", (0.12, 0.08, 0.04), .8, .3, AMBER, 1.2)
    ring = torus("wheel ring", (0, 0, 0), 0.92, 0.1, rim, coll, rot=(math.radians(90), 0, 0), seg=64, ring=12)
    ring.parent = root
    hub = cube("wheel hub", (0, 0, 0), (0.28, 0.28, 0.28), hub_mat, coll, soft=0.08)
    hub.parent = root
    for i in range(3):
        angle = TAU * i / 3
        spoke = cube(
            "wheel spoke %d" % i,
            (math.cos(angle) * 0.48, 0, math.sin(angle) * 0.48),
            (0.42, 0.07, 0.09),
            rim,
            coll,
            rot=(0, -angle, 0),
            soft=0.02,
        )
        spoke.parent = root
    key_rotation(root, 1, (0.02, 0, 0))
    key_rotation(root, FRAME_END, (0.35, 1.0, 0.1))
    return root


def build_trophy(loc):
    coll = collection("TOTEMS")
    root = bpy.data.objects.new("trophy", None)
    coll.objects.link(root)
    root.location = loc
    gold = emission("trophy gold", AMBER, 4.5)
    dark_gold = metal("trophy dark gold", (0.2, 0.1, 0.02), .8, .3, AMBER, 1.0)
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.2, radius2=0.72, depth=0.8, location=(0, 0, 0.8))
    cup = bpy.context.object
    cup.name = "trophy cup"
    apply(cup, gold)
    bevel(cup, 0.03)
    cup.parent = root
    move_to(cup, coll)
    stem = cube("trophy stem", (0, 0, 0.18), (0.16, 0.16, 0.42), dark_gold, coll, soft=0.06)
    stem.parent = root
    base = cube("trophy base", (0, 0, -0.18), (0.55, 0.35, 0.16), dark_gold, coll, soft=0.08)
    base.parent = root
    for side in (-1, 1):
        handle = torus("trophy handle", (side * 0.58, 0, 0.92), 0.28, 0.055, gold, coll, rot=(math.radians(90), 0, 0), seg=48, ring=8)
        handle.scale = (1, 1, 1.45)
        handle.parent = root
    key_rotation(root, 1, (0, 0, -0.3))
    key_rotation(root, FRAME_END, (0.2, 0, 0.45))
    return root


def build_controller(loc):
    coll = collection("TOTEMS")
    root = bpy.data.objects.new("controller", None)
    coll.objects.link(root)
    root.location = loc
    body_mat = metal("controller body", (0.03, 0.08, 0.12), .5, .3, (0.1, 0.65, 0.9), 0.8)
    glow = emission("controller glow", CYAN, 4.0)
    body = cube("controller body", (0, 0, 0), (1.0, 0.18, 0.42), body_mat, coll, soft=0.18)
    body.parent = root
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.18, depth=0.72, location=(side * 0.92, 0, -0.24), rotation=(0, math.radians(side * 28), 0))
        grip = bpy.context.object
        grip.name = "controller grip"
        apply(grip, body_mat)
        bevel(grip, 0.06)
        grip.parent = root
        move_to(grip, coll)
        stick = sphere("controller stick", (side * 0.38, -0.2, 0.04), 0.1, glow, coll, segments=12, rings=6)
        stick.parent = root
    dpad = cube("controller dpad", (-0.55, -0.2, 0.06), (0.17, 0.05, 0.17), glow, coll, soft=0.02)
    dpad.parent = root
    key_rotation(root, 1, (0.1, 0, -0.2))
    key_rotation(root, FRAME_END, (0.35, 0.6, 0.25))
    return root


def build_card(loc, label, sub, color, spin, idx):
    coll = collection("CARDS")
    root = bpy.data.objects.new("card " + label, None)
    coll.objects.link(root)
    root.location = loc
    root.rotation_euler = (0, 0, spin)
    back = cube("card glow " + label, (0, 0, 0), (0.72, 0.025, 1.04), emission("card " + label, color, 1.8), coll, soft=0.03)
    back.parent = root
    front = cube("card face " + label, (0, -0.05, 0), (0.68, 0.035, 1.0), metal("card face mat", (0.01, 0.02, 0.04), .2, .45), coll, soft=0.03)
    front.parent = root
    title = text("card title " + label, label, (0, -0.1, 0.34), 0.52, emission("card text " + label, color, 4.0), coll, extrude=0.005)
    title.parent = root
    subtitle = text("card sub " + label, sub, (0, -0.1, -0.42), 0.12, emission("card sub mat", (0.45, 0.68, 0.8), 2.0), coll, extrude=0.002)
    subtitle.parent = root
    index = text("card idx " + label, "%02d" % idx, (0, -0.1, 0.88), 0.14, emission("card idx mat", color, 2.0), coll, extrude=0.002)
    index.parent = root
    key_rotation(root, 1, (0, 0, spin))
    key_rotation(root, FRAME_END, (0.02, 0.13, spin + 0.5))
    key_location(root, 1, loc)
    key_location(root, FRAME_END, (loc[0], loc[1], loc[2] + 0.35))
    return root


# ---------------------------------------------------------------------------
# final monument
# ---------------------------------------------------------------------------

def build_monument():
    coll = collection("MONUMENT")
    ivory = emission("monument ivory", (0.62, 0.82, 1.0), 3.0)
    amber = emission("monument amber", AMBER, 4.5)
    soft = emission("monument soft", (0.35, 0.58, 0.8), 1.1)

    # a dark slab makes the light feel monumental
    slab = cube("archive slab", (0, 73.4, 5.3), (8.6, 0.7, 5.8), metal("slab", (0.005, 0.012, 0.025), .35, .2), coll, soft=0.12)
    slab_parts = [slab]
    for side in (-1, 1):
        slab_parts.append(cube("slab edge", (side * 8.6, 72.85, 5.3), (0.04, 0.03, 5.8), soft, coll))

    # a slim frame around the monument (the old outer torus produced a
    # screen-space streak in Eevee; use straight rails instead)
    for z in (8.2, 2.4):
        slab_parts.append(cube("monument rail", (0, 72.6, z), (5.4, 0.02, 0.02), soft, coll, soft=0))
    for x in (-5.4, 5.4):
        slab_parts.append(cube("monument post", (x, 72.6, 5.3), (0.02, 0.02, 2.9), soft, coll, soft=0))

    # bright inner aperture
    torus("monument inner", (0, 70.6, 5.4), 4.3, 0.045, amber, coll, seg=96)

    title = text("STEAM", "STEAM", (0, 69.85, 5.65), 2.25, ivory, coll, extrude=0.06)
    subtitle = text("numbers", "150,279 GAMES  ·  18 YEARS", (0, 69.8, 3.65), 0.72, amber, coll, extrude=0.015)
    tagline = text("tagline", "ONE PLATFORM  ·  EVERY STORY", (0, 69.75, 2.65), 0.34, soft, coll, extrude=0.006)
    for obj in (title, subtitle, tagline):
        key_scale(obj, 1, (0.01, 0.01, 0.01))
        key_scale(obj, 112, (0.01, 0.01, 0.01))
        key_scale(obj, 158, (1, 1, 1))
        key_scale(obj, FRAME_END, (1, 1, 1))

    # the slab is a reveal element, not a black hole floating in the tunnel
    for obj in slab_parts:
        base = (obj.scale.x, obj.scale.y, obj.scale.z)
        key_scale(obj, 1, (0.001, 0.001, 0.001))
        key_scale(obj, 150, (0.001, 0.001, 0.001))
        key_scale(obj, 158, base)
        key_scale(obj, FRAME_END, base)

    point_light("monument key", (0, 66, 12), (0.55, 0.8, 1.0), 2600, radius=12)
    point_light("monument amber", (0, 66, 2), AMBER, 1100, radius=10)


def build_logo(loc, size, coll):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = "steam emblem"
    image_path = os.path.join(ROOT, "assets", "steam-logo.png")
    mat = bpy.data.materials.new("steam emblem mat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(image_path, check_existing=True)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 3.2
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(transparent.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        mat.surface_render_method = "BLENDED"
        mat.blend_method = "BLEND"
    except Exception:
        pass
    obj.data.materials.append(mat)
    move_to(obj, coll)
    return obj


# ---------------------------------------------------------------------------
# camera / render
# ---------------------------------------------------------------------------

def build_camera():
    cam_data = bpy.data.cameras.new("archive camera")
    cam = bpy.data.objects.new("archive camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_data.lens = 34
    cam_data.sensor_width = 36

    path = [
        (1, (0.0, -12.0, 2.2), (math.radians(90), 0, 0)),
        (36, (0.25, -2.0, 2.45), (math.radians(90), 0, 0.01)),
        (68, (-0.35, 10.0, 2.75), (math.radians(90), 0, 0.025)),
        (102, (0.35, 23.0, 3.15), (math.radians(90), 0, 0.015)),
        (136, (-0.2, 36.0, 4.1), (math.radians(90), 0, -0.02)),
        (164, (0.15, 49.0, 5.1), (math.radians(91), 0, -0.03)),
        (184, (0.0, 56.0, 5.75), (math.radians(92), 0, -0.02)),
        (FRAME_END, (0.0, 57.2, 5.9), (math.radians(92), 0, -0.015)),
    ]
    for frame, loc, rot in path:
        key_location(cam, frame, loc)
        key_rotation(cam, frame, rot)
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
    return cam


def render_setup():
    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 48
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    # compositor bloom: the emissive archive rings should bleed into the void
    scene.use_nodes = True
    nt = scene.node_tree
    nt.nodes.clear()
    layers = nt.nodes.new("CompositorNodeRLayers")
    glare = nt.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = 0.8
    glare.size = 7
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(layers.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], comp.inputs["Image"])


def render():
    scene = bpy.context.scene
    if TEST:
        frame = 20
        if "--frame" in sys.argv:
            try:
                frame = int(sys.argv[sys.argv.index("--frame") + 1])
            except (IndexError, ValueError):
                pass
        scene.render.resolution_x = 960
        scene.render.resolution_y = 540
        scene.render.resolution_percentage = 100
        scene.frame_end = max(36, frame)
        scene.render.image_settings.file_format = "PNG"
        tag = ""
        if "--tag" in sys.argv:
            try:
                tag = "_" + sys.argv[sys.argv.index("--tag") + 1].replace(" ", "_")
            except IndexError:
                pass
        scene.render.filepath = os.path.join(OUT, "test_frame_%03d%s.png" % (frame, tag))
        scene.frame_set(frame)
        bpy.ops.render.render(write_still=True)
        return

    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "steam-archive.blend"))

    # poster: a frame after the first gate opens
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(OUT, "poster.png")
    scene.frame_set(48)
    bpy.ops.render.render(write_still=True)

    # H.264 MP4, no audio, browser friendly
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.filepath = os.path.join(OUT, "steam-archive-intro.mp4")
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    bpy.ops.render.render(animation=True)


def main():
    reset()
    build_world()
    build_stars()
    build_gate(1, 7.0, 6.2, CYAN)
    build_gate(2, 21.0, 7.2, MINT)
    build_gate(3, 35.0, 8.2, PURPLE)
    build_gate(4, 49.0, 9.2, AMBER)
    build_card((-5.3, 12.5, 1.8), "RPG", "STORIES", PURPLE, 0.12, 1)
    build_card((5.4, 16.0, 2.9), "FPS", "SQUADS", CYAN, -0.1, 2)
    build_card((-5.7, 29.0, 2.5), "INDIE", "RISK", MINT, 0.18, 3)
    build_card((5.8, 42.0, 2.0), "SIM", "SYSTEMS", AMBER, -0.15, 4)
    build_dice((-5.8, 8.5, 2.4))
    build_sword((5.9, 23.0, 2.1))
    build_controller((-6.1, 31.0, 1.8))
    build_wheel((6.0, 38.0, 2.2))
    build_trophy((-6.2, 47.0, 2.2))
    build_monument()
    build_camera()
    render_setup()

    if "--hide-all" in sys.argv:
        for obj in bpy.data.objects:
            if obj.type in {"MESH", "FONT", "CURVE"}:
                obj.hide_render = True
                print("HIDDEN", obj.name)

    if "--hide" in sys.argv:
        try:
            needle = sys.argv[sys.argv.index("--hide") + 1].lower()
        except IndexError:
            needle = ""
        for obj in bpy.data.objects:
            if needle and needle in obj.name.lower():
                obj.hide_render = True
                print("HIDDEN", obj.name)

    if "--inspect" in sys.argv:
        scene = bpy.context.scene
        scene.frame_set(168)
        cam = scene.camera
        rows = []
        for obj in bpy.data.objects:
            if obj.type not in {"MESH", "FONT", "CURVE"}:
                continue
            d = obj.dimensions
            dist = (obj.matrix_world.translation - cam.matrix_world.translation).length
            if max(d) > 3 or (max(d) > 1.0 and min(d) < 0.08):
                rows.append((dist, obj.name, tuple(round(v, 3) for v in d), tuple(round(v, 2) for v in obj.matrix_world.translation)))
        for row in sorted(rows, key=lambda r: r[0])[:30]:
            print("INSPECT", row)

        # Ray-cast through the suspicious bright diagonal in the final shot.
        frame = cam.data.view_frame(scene=scene)
        origin = cam.matrix_world.translation
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for u, v in ((0.16, 0.66), (0.42, 0.55), (0.72, 0.44), (0.9, 0.34)):
            local = (
                frame[0] * (u * (1 - v))
                + frame[1] * (u * v)
                + frame[2] * ((1 - u) * v)
                + frame[3] * ((1 - u) * (1 - v))
            )
            direction = (cam.matrix_world.to_quaternion() @ local).normalized()
            hit, loc, normal, index, obj, matrix = scene.ray_cast(depsgraph, origin, direction)
            print("RAY", u, v, hit, obj.name if obj else None, tuple(round(vv, 2) for vv in loc))
        return

    render()


if __name__ == "__main__":
    main()
