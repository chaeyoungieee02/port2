import bpy
import math
import os
import random
# ============================================================
# CONFIGURATION
# ============================================================
TEXTURE_DIR = r"C:\tex"
RENDER_ENGINE = "CYCLES"   # or "BLENDER_EEVEE"
RESOLUTION_X = 1920
RESOLUTION_Y = 1080
FRAME_START = 1
FRAME_END = 1500
USE_BLOOM = True
USE_MOTION_BLUR = False

def resolve_asset_path(filename):
    """Return full path to a texture file in TEXTURE_DIR."""
    return os.path.join(TEXTURE_DIR, filename)

def fetch_surface_map(pname):
    """Return texture path for a planet using the planet_name.jpg convention."""
    return resolve_asset_path(f"{pname.lower()}.jpg")

# ============================================================
# SECTION 1 - SCENE SETUP
# ============================================================
def build_environment():
    # Clear everything robustly
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)

    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end   = FRAME_END

    # Render engine
    scene.render.engine = RENDER_ENGINE
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.film_transparent = False

    if RENDER_ENGINE == "BLENDER_EEVEE":
        eevee = scene.eevee
        eevee.use_bloom = USE_BLOOM
        eevee.bloom_intensity = 0.5    # Massive bloom for glowing sun and nebula
        eevee.bloom_threshold = 0.8    # Allow softer elements to glow
        eevee.bloom_radius = 6.0       # Spread the glow out wider
        eevee.use_ssr = True
        eevee.use_soft_shadows = True
        eevee.shadow_cube_size = '1024'
        eevee.taa_render_samples = 64
        if USE_MOTION_BLUR:
            eevee.use_motion_blur = True
    else:
        cycles = scene.cycles
        cycles.samples = 128
        if USE_MOTION_BLUR:
            scene.render.use_motion_blur = True

        # In Cycles, Bloom must be done via the Compositor using a Glare node
        if USE_BLOOM:
            scene.use_nodes = True
            tree = scene.node_tree
            tree.nodes.clear()

            rlayers = tree.nodes.new(type='CompositorNodeRLayers')
            rlayers.location = (0, 0)

            glare = tree.nodes.new(type='CompositorNodeGlare')
            glare.location = (300, 0)
            glare.glare_type = 'FOG_GLOW'
            glare.quality = 'HIGH'
            glare.threshold = 0.8
            glare.size = 9  # Max size for glow spread

            comp = tree.nodes.new(type='CompositorNodeComposite')
            comp.location = (600, 0)

            tree.links.new(rlayers.outputs['Image'], glare.inputs['Image'])
            tree.links.new(glare.outputs['Image'], comp.inputs['Image'])

    # World - starfield
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    wnt.nodes.clear()

    bg_node  = wnt.nodes.new("ShaderNodeBackground")
    out_node = wnt.nodes.new("ShaderNodeOutputWorld")
    out_node.location = (300, 0)

    # 1. Procedural Cosmic Nebula
    noise = wnt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-600, 200)
    noise.inputs["Scale"].default_value = 1.2
    noise.inputs["Detail"].default_value = 15.0
    noise.inputs["Roughness"].default_value = 0.55

    ramp = wnt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-400, 200)
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.05, 0.005, 0.01, 1.0) # Subtle lowkey purple space dust
    ramp.color_ramp.elements.new(0.85)
    ramp.color_ramp.elements[2].color = (0.15, 0.05, 0.01, 1.0) # Lowkey dark orange dust

    wnt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    # 2. Base Stars
    stars_path = resolve_asset_path("stars.jpg")
    mix_node = wnt.nodes.new("ShaderNodeMixRGB")
    mix_node.blend_type = 'ADD'
    mix_node.inputs[0].default_value = 1.0
    mix_node.location = (-150, 0)

    if os.path.exists(stars_path):
        tex_coord = wnt.nodes.new("ShaderNodeTexCoord")
        mapping    = wnt.nodes.new("ShaderNodeMapping")
        img_node   = wnt.nodes.new("ShaderNodeTexEnvironment")
        tex_coord.location  = (-800, -200)
        mapping.location    = (-600, -200)
        img_node.location   = (-400, -200)
        try:
            img_node.image = bpy.data.images.load(stars_path)
        except Exception:
            pass
        wnt.links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        wnt.links.new(mapping.outputs["Vector"],      img_node.inputs["Vector"])
        wnt.links.new(img_node.outputs["Color"], mix_node.inputs[1])
    else:
        mix_node.inputs[1].default_value = (0.0, 0.0, 0.0, 1.0)

    wnt.links.new(ramp.outputs["Color"], mix_node.inputs[2])
    wnt.links.new(mix_node.outputs["Color"], bg_node.inputs["Color"])
    bg_node.inputs["Strength"].default_value = 0.5

    wnt.links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])
    return scene

# ============================================================
# SECTION 2 - MATERIAL HELPERS
# ============================================================
def make_surface_shader(name, texture_path, emission_color=None,
                               emission_strength=0.0, roughness=0.8,
                               metallic=0.0, alpha=1.0, blend_mode=None, bump_path=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial")
    out.location   = (600, 0)
    bsdf  = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location  = (200, 0)
    bsdf.inputs["Roughness"].default_value  = roughness
    bsdf.inputs["Metallic"].default_value   = metallic

    if texture_path and os.path.exists(texture_path):
        coord = nodes.new("ShaderNodeTexCoord")
        coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping")
        uvmap.location  = (-400, 0)
        img   = nodes.new("ShaderNodeTexImage")
        img.location    = (-150, 50)
        try:
            img.image = bpy.data.images.load(texture_path, check_existing=True)
        except Exception:
            pass
        links.new(coord.outputs["UV"],     uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"], img.inputs["Vector"])
        links.new(img.outputs["Color"],    bsdf.inputs["Base Color"])

        if alpha < 1.0:
            links.new(img.outputs["Alpha"], bsdf.inputs["Alpha"])
            mat.blend_method  = blend_mode or "BLEND"
            mat.shadow_method = "CLIP"

    if bump_path and os.path.exists(bump_path):
        if not ("coord" in locals() and "uvmap" in locals()):
            coord = nodes.new("ShaderNodeTexCoord")
            coord.location = (-600, 0)
            uvmap = nodes.new("ShaderNodeMapping")
            uvmap.location  = (-400, 0)
        bump_img = nodes.new("ShaderNodeTexImage")
        bump_img.location = (-150, -250)
        bump_node = nodes.new("ShaderNodeBump")
        bump_node.location = (50, -250)
        try:
            bump_img.image = bpy.data.images.load(bump_path, check_existing=True)
            bump_img.image.colorspace_settings.name = 'Non-Color'
        except Exception:
            pass
        links.new(uvmap.outputs["Vector"], bump_img.inputs["Vector"])
        links.new(bump_img.outputs["Color"], bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])
        bump_node.inputs["Distance"].default_value = 0.2

    if emission_color and emission_strength > 0:
        for emission_key in ["Emission Color", "Emission"]:
            if emission_key in bsdf.inputs:
                bsdf.inputs[emission_key].default_value = (*emission_color, 1)
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def make_star_shader():
    mat   = bpy.data.materials.new(name="Sun_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial")
    out.location   = (600, 0)
    emit  = nodes.new("ShaderNodeEmission")
    emit.location  = (200, 0)
    emit.inputs["Strength"].default_value = 15.0
    emit.inputs["Color"].default_value    = (1.0, 0.35, 0.02, 1.0)

    tex_path = resolve_asset_path("sun.jpg")
    if os.path.exists(tex_path):
        coord = nodes.new("ShaderNodeTexCoord")
        coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping")
        uvmap.location  = (-400, 0)
        img   = nodes.new("ShaderNodeTexImage")
        img.location    = (-150, 0)
        try:
            img.image = bpy.data.images.load(tex_path, check_existing=True)
        except Exception:
            pass
        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (-10, 100)
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Fac"].default_value = 0.6
        mix.inputs["Color2"].default_value = (1.0, 0.75, 0.2, 1.0)
        links.new(coord.outputs["UV"],     uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"], img.inputs["Vector"])
        links.new(img.outputs["Color"],    mix.inputs["Color1"])
        links.new(mix.outputs["Color"],    emit.inputs["Color"])

    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat

def make_glow_layer():
    mat   = bpy.data.materials.new(name="Earth_Atmo")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    trans = nodes.new("ShaderNodeBsdfTransparent")
    trans.location = (-100, 100)
    emit  = nodes.new("ShaderNodeEmission")
    emit.location  = (-100, -50)
    emit.inputs["Color"].default_value    = (0.2, 0.5, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 0.3

    fac = nodes.new("ShaderNodeLayerWeight")
    fac.location = (-300, 0)
    fac.inputs["Blend"].default_value = 0.45
    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (400, 0)

    links.new(fac.outputs["Facing"],    mix.inputs["Fac"])
    links.new(trans.outputs["BSDF"],    mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"],    out.inputs["Surface"])

    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"
    return mat

def make_disc_shader(ring_texture=None):
    mat   = bpy.data.materials.new(name="Ring_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial")
    out.location  = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Alpha"].default_value     = 0.55

    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"

    if ring_texture and os.path.exists(ring_texture):
        coord = nodes.new("ShaderNodeTexCoord")
        coord.location = (-600, 0)
        img   = nodes.new("ShaderNodeTexImage")
        img.location    = (-150, 50)
        bw    = nodes.new("ShaderNodeRGBToBW")
        bw.location     = (50, -50)
        try:
            img.image = bpy.data.images.load(ring_texture, check_existing=True)
        except Exception:
            pass
        links.new(coord.outputs["UV"],   img.inputs["Vector"])
        links.new(img.outputs["Color"],  bsdf.inputs["Base Color"])
        links.new(img.outputs["Color"],  bw.inputs["Color"])
        links.new(bw.outputs["Val"],     bsdf.inputs["Alpha"])
    else:
        bsdf.inputs["Base Color"].default_value = (0.85, 0.78, 0.65, 1.0)

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

# ============================================================
# SECTION 3 - OBJECT HELPERS
# ============================================================
def add_globe(name, radius, location=(0, 0, 0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=location,
        segments=segments, ring_count=rings)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj

def add_flat_ring(name, radius, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=128, radius=radius, depth=0.001,
        location=location, rotation=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj

def add_anchor(name, location=(0, 0, 0)):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj

def add_light_source(name, location, energy, radius=0.5, color=(1, 0.9, 0.7)):
    bpy.ops.object.light_add(type='POINT', location=location)
    light = bpy.context.active_object
    light.name = name
    light.data.energy       = energy
    light.data.color        = color
    light.data.shadow_soft_size = radius
    return light

def assign_shader(obj, mat):
    if obj.data.materials:
        obj.data.materials = mat
    else:
        obj.data.materials.append(mat)

# ============================================================
# SECTION 4 - PLANET DEFINITIONS
# ============================================================
PLANET_DATA = [
    ("Mercury", 0.11,  12,     88,   58,  0.03,  (0.6, 0.5, 0.45, 1)),
    ("Venus",   0.28,  18,    225,  243,  177.4, (0.9, 0.8, 0.5,  1)),
    ("Earth",   0.30,  25,    365,    1,   23.4, (0.2, 0.5, 0.9,  1)),
    ("Mars",    0.16,  34,    687,   1.03, 25.2, (0.8, 0.4, 0.2,  1)),
    ("Jupiter", 3.36,  55,   4333,   0.41, 3.1,  (0.8, 0.7, 0.55, 1)),
    ("Saturn",  2.83,  80,  10759,   0.45, 26.7, (0.9, 0.85, 0.6, 1)),
    ("Uranus",  1.20, 105,  30688,   0.72, 97.8, (0.5, 0.85, 0.9, 1)),
    ("Neptune", 1.16, 125,  60182,   0.67, 28.3, (0.2, 0.4, 0.9,  1)),
    ("Pluto",   0.05, 150,  90560,   6.39, 122.5, (0.6, 0.5, 0.4,  1)),
]

SUN_RADIUS = 8.0
SPEED_SCALE = 1.5

# ============================================================
# SECTION 5 - BUILD SOLAR SYSTEM
# ============================================================
def build_system():
    planets = {}

    # ----- SUN -----
    sun_obj = add_globe("Sun", SUN_RADIUS)
    sun_mat = make_star_shader()
    assign_shader(sun_obj, sun_mat)
    sun_obj.visible_shadow = False

    sun_light = add_light_source("SunLight", (0, 0, 0), energy=150000, radius=SUN_RADIUS, color=(1.0, 0.95, 0.9))
    sun_light.data.use_shadow = False
    sun_light.data.use_custom_distance = True
    sun_light.data.cutoff_distance     = 600.0

    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(45), math.radians(45), 0))
    fill = bpy.context.active_object
    fill.name = "AmbientFill"
    fill.data.energy = 0.01
    fill.data.color = (0.3, 0.35, 0.5)
    fill.data.use_shadow = False

    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(-45), math.radians(-135), 0))
    fill2 = bpy.context.active_object
    fill2.name = "AmbientFill2"
    fill2.data.energy = 0.03
    fill2.data.color = (0.7, 0.8, 1.0)
    fill2.data.use_shadow = False

    # ----- PLANETS -----
    for (pname, prad, orbit_r, orb_period, rot_period, axial_tilt, base_color) in PLANET_DATA:
        pivot = add_anchor(f"{pname}_Pivot")
        planet = add_globe(pname, prad, location=(orbit_r, 0, 0))
        planet.parent = pivot
        planet.rotation_euler.x = math.radians(axial_tilt)

        tpath = fetch_surface_map(pname)
        bpath = resolve_asset_path("pluto_bump.jpg") if pname == "Pluto" else None
        mat = make_surface_shader(
            f"{pname}_Mat", tpath,
            roughness=0.85, metallic=0.0,
            bump_path=bpath)
        if not os.path.exists(tpath):
            mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = base_color
        assign_shader(planet, mat)

        planets[pname] = {"pivot": pivot, "planet": planet, "orbit_r": orbit_r, "radius": prad}

    # ----- SATURN RINGS -----
    saturn_info = planets["Saturn"]
    sat_obj     = saturn_info["planet"]
    sat_r       = saturn_info["radius"]

    ring_tex_path = resolve_asset_path("saturn_ring.jpg")
    ring = add_flat_ring("Saturn_Ring", radius=sat_r * 2.2, location=(0, 0, 0))
    ring.parent = sat_obj
    ring_mat = make_disc_shader(ring_tex_path if os.path.exists(ring_tex_path) else None)
    assign_shader(ring, ring_mat)

    # ----- MOON -----
    earth_info = planets["Earth"]
    earth_obj  = earth_info["planet"]
    earth_r    = earth_info["radius"]

    moon_radius = earth_r * 0.27
    moon_orbit_r = earth_r * 3.0
    moon_obj = add_globe("Moon", moon_radius, location=(moon_orbit_r, 0, 0))
    moon_obj.parent = earth_obj

    moon_tex_path = resolve_asset_path("moon.jpg")
    moon_mat = make_surface_shader("Moon_Mat", moon_tex_path, roughness=0.9, metallic=0.0)
    assign_shader(moon_obj, moon_mat)


    # ----- EARTH SATELLITE (imported from sat.blend) -----
    sat_blend_path = r"C:\tex\sat.blend"
    sat_orbit_r = earth_r * 1.6   # Low orbit, closer than the Moon
    sat_pivot = add_anchor("Satellite_Pivot")
    sat_pivot.parent = earth_obj
    sat_pivot.rotation_euler = (math.radians(28), 0, 0)  # slight orbital inclination

    # Append all objects from sat.blend
    sat_objects_before = set(bpy.data.objects.keys())
    try:
        with bpy.data.libraries.load(sat_blend_path, link=False) as (data_from, data_to):
            data_to.objects = data_from.objects
        sat_objects_after = set(bpy.data.objects.keys())
        new_sat_objs = [bpy.data.objects[n] for n in (sat_objects_after - sat_objects_before)]

        if new_sat_objs:
            # Link all imported objects into the scene and parent to pivot
            for obj in new_sat_objs:
                bpy.context.collection.objects.link(obj)

            # Find the root (object with no parent among the imported set)
            imported_names = {o.name for o in new_sat_objs}
            roots = [o for o in new_sat_objs if o.parent is None or o.parent.name not in imported_names]
            sat_root = roots[0] if roots else new_sat_objs[0]

            # Scale and position the satellite
            sat_root.location = (sat_orbit_r, 0, 0)
            sat_root.scale = (earth_r * 0.25, earth_r * 0.25, earth_r * 0.25)
            sat_root.parent = sat_pivot
            sat_body = sat_root
        else:
            raise Exception("No objects found in sat.blend")

    except Exception as e:
        print(f"  -> WARNING: Could not load sat.blend ({e}), falling back to primitive")
        # Fallback: simple box satellite
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sat_orbit_r, 0, 0))
        sat_body = bpy.context.active_object
        sat_body.name = "Satellite_Body"
        sat_body.scale = (earth_r * 0.25, earth_r * 0.12, earth_r * 0.08)
        bpy.ops.object.transform_apply(scale=True)
        sat_body.parent = sat_pivot

    # Animate satellite orbit - fast, close orbit around Earth
    sat_pivot.rotation_euler = (math.radians(28), 0, 0)
    sat_pivot.keyframe_insert(data_path="rotation_euler", frame=1)
    sat_pivot.rotation_euler = (math.radians(28), 0, math.radians(360 * 12))
    sat_pivot.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
    for fcurve in sat_pivot.animation_data.action.fcurves:
        for kf in fcurve.keyframe_points:
            kf.interpolation = 'LINEAR'

    # Slow tumble on the satellite itself
    sat_body.rotation_euler = (0, 0, 0)
    sat_body.keyframe_insert(data_path="rotation_euler", frame=1)
    sat_body.rotation_euler.y = math.radians(360 * 3)
    sat_body.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
    for fcurve in sat_body.animation_data.action.fcurves:
        for kf in fcurve.keyframe_points:
            kf.interpolation = 'LINEAR'


    # ----- JUPITER MOONS -----
    jup_info = planets["Jupiter"]
    jup_obj  = jup_info["planet"]
    jup_r    = jup_info["radius"]

    jup_moons = [
        ("Io", jup_r * 0.025, jup_r * 1.5, "io.jpg"),
        ("Europa", jup_r * 0.02, jup_r * 2.0, "europa.jpg"),
        ("Ganymede", jup_r * 0.035, jup_r * 2.6, "ganymede.jpg"),
        ("Callisto", jup_r * 0.032, jup_r * 3.3, "callisto.jpg")
    ]

    for i, (m_name, m_rad, m_dist, m_tex) in enumerate(jup_moons):
        angle = i * (math.pi / 2)
        lx = m_dist * math.cos(angle)
        ly = m_dist * math.sin(angle)
        m_obj = add_globe(m_name, m_rad, location=(lx, ly, 0))
        m_obj.parent = jup_obj

        m_tex_path = resolve_asset_path(m_tex)
        m_mat = make_surface_shader(f"{m_name}_Mat", m_tex_path, roughness=0.9, metallic=0.0)
        assign_shader(m_obj, m_mat)

    return planets

# ============================================================
# SECTION 5b - ORBIT LINES
# ============================================================
def render_orbit_lines():
    """Draw a faint emissive circle at each planet's orbital radius."""

    mat = bpy.data.materials.new("Orbit_Line_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (400, 0)
    emit = nodes.new("ShaderNodeEmission");        emit.location = (100, 0)
    emit.inputs["Color"].default_value    = (0.4, 0.6, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 0.7  # Below bloom threshold to prevent bright glowing

    # We add a Mix Shader to animate opacity
    trans = nodes.new("ShaderNodeBsdfTransparent"); trans.location = (100, 100)
    mix = nodes.new("ShaderNodeMixShader"); mix.location = (250, 50)
    mix.name = "OrbitFadeMix"
    mix.inputs[0].default_value = 1.0 # 0 = transparent, 1 = emission

    links.new(trans.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])

    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"

    ORBIT_SEGMENTS = 256

    for (pname, prad, orbit_r, *_rest) in PLANET_DATA:
        curve_data = bpy.data.curves.new(name=f"Orbit_{pname}", type='CURVE')
        curve_data.dimensions          = '3D'
        curve_data.resolution_u        = 12
        curve_data.render_resolution_u = 24
        curve_data.bevel_depth         = 0.014  # Physically thicker so they don't vanish from afar without bloom
        curve_data.use_fill_caps       = True

        spline = curve_data.splines.new('POLY')
        spline.use_cyclic_u = True
        spline.points.add(ORBIT_SEGMENTS - 1)

        for i, pt in enumerate(spline.points):
            angle = (2 * math.pi * i) / ORBIT_SEGMENTS
            pt.co = (
                orbit_r * math.cos(angle),
                orbit_r * math.sin(angle),
                0.0,
                1.0
            )

        orbit_obj = bpy.data.objects.new(f"Orbit_{pname}", curve_data)
        bpy.context.collection.objects.link(orbit_obj)
        orbit_obj.data.materials.append(mat)

# ============================================================
# SECTION 5c - SCATTERED ASTEROIDS
# ============================================================
def place_debris():
    """
    Places a small number of individual jagged asteroids drifting
    through the scene (rather than a dense ring-shaped belt). Each
    rock gets its own random position, slow tumble, and gentle drift.
    """
    field_root = add_anchor("AsteroidField_Root")

    ast_mat = bpy.data.materials.new("Asteroid_Mat")
    ast_mat.use_nodes = True
    nodes = ast_mat.node_tree.nodes
    links = ast_mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    bsdf.inputs["Roughness"].default_value = 0.97
    bsdf.inputs["Metallic"].default_value  = 0.0

    ast_tex_path = resolve_asset_path("asteroid.jpg")
    if os.path.exists(ast_tex_path):
        coord = nodes.new("ShaderNodeTexCoord")
        coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping")
        uvmap.location = (-400, 0)
        img = nodes.new("ShaderNodeTexImage")
        img.location = (-150, 50)
        try:
            img.image = bpy.data.images.load(ast_tex_path, check_existing=True)
        except Exception:
            pass
        # Slight per-vertex tint variation so the rocks don't all look identical
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (-600, -250)
        noise.inputs["Scale"].default_value = 8.0
        tint_ramp = nodes.new("ShaderNodeValToRGB")
        tint_ramp.location = (-400, -250)
        tint_ramp.color_ramp.elements[0].color = (0.75, 0.75, 0.75, 1.0)
        tint_ramp.color_ramp.elements[1].color = (1.1, 1.05, 1.0, 1.0)
        tint_mix = nodes.new("ShaderNodeMixRGB")
        tint_mix.location = (-150, -150)
        tint_mix.blend_type = 'MULTIPLY'
        tint_mix.inputs["Fac"].default_value = 0.8

        links.new(coord.outputs["UV"], uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"], img.inputs["Vector"])
        links.new(noise.outputs["Fac"], tint_ramp.inputs["Fac"])
        links.new(img.outputs["Color"], tint_mix.inputs["Color1"])
        links.new(tint_ramp.outputs["Color"], tint_mix.inputs["Color2"])
        links.new(tint_mix.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (0.30, 0.27, 0.24, 1.0)
        print("  -> WARNING: asteroid.jpg not found, using fallback color")

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    count = 80  # more rocks scattered through the scene

    asteroids = []

    for i in range(count):
        # Sculpt a jagged rock from an ico-sphere with random vertex displacement
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.7)
        ast = bpy.context.active_object
        ast.name = f"Asteroid_{i:02d}"

        ast.scale = (
            random.uniform(0.5, 1.6),
            random.uniform(0.5, 1.6),
            random.uniform(0.4, 1.3),
        )
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        for v in ast.data.vertices:
            jitter = 1.0 + random.uniform(-0.35, 0.35)
            v.co.x *= jitter
            v.co.y *= jitter
            v.co.z *= jitter * (1.0 + random.uniform(-0.2, 0.2))

        bpy.ops.object.shade_flat()
        assign_shader(ast, ast_mat)

        # Scatter rocks loosely through the scene rather than in a ring
        radius = random.uniform(20.0, 170.0)
        angle  = random.uniform(0, 2 * math.pi)
        height = random.uniform(-25.0, 25.0)

        ast.location = (radius * math.cos(angle), radius * math.sin(angle), height)
        s = random.uniform(0.6, 2.4)
        ast.scale = (s, s, s)
        ast.rotation_euler = (
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2),
        )
        ast.parent = field_root
        asteroids.append(ast)

    # Give each rock its own slow tumble and a gentle linear drift
    for ast in asteroids:
        start_rot = tuple(ast.rotation_euler)
        ast.keyframe_insert(data_path="rotation_euler", frame=1)

        spin_axis = random.choice(['x', 'y', 'z'])
        spin_amount = math.radians(random.uniform(40, 160))
        end_rot = list(start_rot)
        axis_idx = {'x': 0, 'y': 1, 'z': 2}[spin_axis]
        end_rot[axis_idx] += spin_amount
        ast.rotation_euler = tuple(end_rot)
        ast.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

        start_loc = tuple(ast.location)
        ast.keyframe_insert(data_path="location", frame=1)

        drift = (
            random.uniform(-6.0, 6.0),
            random.uniform(-6.0, 6.0),
            random.uniform(-3.0, 3.0),
        )
        ast.location = (
            start_loc[0] + drift[0],
            start_loc[1] + drift[1],
            start_loc[2] + drift[2],
        )
        ast.keyframe_insert(data_path="location", frame=FRAME_END)

        if ast.animation_data and ast.animation_data.action:
            for fcurve in ast.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'LINEAR'

    print(f"  -> Scattered {count} individual asteroids through the scene")
    return field_root

# ============================================================
# SECTION 6 - ANIMATION
# ============================================================
def run_motion(planets):
    scene = bpy.context.scene
    scene.frame_set(1)

    for (pname, prad, orbit_r, orb_period, rot_period, axial_tilt, base_color) in PLANET_DATA:
        pivot  = planets[pname]["pivot"]
        planet = planets[pname]["planet"]

        deg_per_frame = 360.0 / (orb_period / SPEED_SCALE)
        pivot.rotation_euler = (0, 0, 0)
        pivot.keyframe_insert(data_path="rotation_euler", frame=1)
        total_degrees = deg_per_frame * FRAME_END
        pivot.rotation_euler.z = math.radians(total_degrees)
        pivot.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

        for fcurve in pivot.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

        rot_deg_per_frame = 0.5
        planet.rotation_euler = (math.radians(axial_tilt), 0, 0)
        planet.keyframe_insert(data_path="rotation_euler", frame=1)
        planet.rotation_euler = (math.radians(axial_tilt), 0, math.radians(rot_deg_per_frame * FRAME_END))
        planet.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

        for fcurve in planet.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

    sun = bpy.data.objects.get("Sun")
    if sun:
        sun.rotation_euler.z = 0
        sun.keyframe_insert(data_path="rotation_euler", frame=1)
        sun.rotation_euler.z = math.radians(360 * 2)
        sun.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
        for fcurve in sun.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

# ============================================================
# SECTION 7 - PLANET LABELS
# ============================================================
def add_name_tags(planets, cam_obj, blocks):
    label_objects = {}
    for (pname, prad, orbit_r, orb_period, rot_period, axial_tilt, base_color) in PLANET_DATA:
        planet = planets[pname]["planet"]
        pivot = planets[pname]["pivot"]

        label_prad = prad * 2.5 if pname == "Saturn" else prad

        billboard_rig = add_anchor(f"LabelRig_{pname}", location=(orbit_r, 0, 0))
        billboard_rig.parent = pivot

        c_track = billboard_rig.constraints.new(type='TRACK_TO')
        c_track.target = cam_obj
        c_track.track_axis = 'TRACK_Z'
        c_track.up_axis = 'UP_Y'

        bpy.ops.object.text_add(location=(0, 0, 0))
        txt_obj = bpy.context.active_object
        txt_obj.name = f"Label_{pname}"
        txt_obj.parent = billboard_rig
        txt_obj.data.body = pname.upper()
        txt_obj.data.size = label_prad * 0.35
        txt_obj.data.align_x = 'LEFT'
        txt_obj.data.space_character = 1.1
        txt_obj.location = (label_prad * 1.3, label_prad * 0.2, 0)

        # Font priority: clean & minimal — geometric sans-serif, light tracking
        font_candidates = [
            r"C:\tex\raleway.ttf",               # Raleway (user-supplied, ideal clean pick)
            r"C:\tex\montserrat.ttf",            # Montserrat (user-supplied)
            r"C:\Windows\Fonts\gill.ttf",        # Gill Sans
            r"C:\Windows\Fonts\gilsanub.ttf",   # Gill Sans Bold
            r"C:\Windows\Fonts\century.ttf",    # Century Gothic
            r"C:\Windows\Fonts\GOTHIC.TTF",     # Century Gothic (alt path)
            r"C:\Windows\Fonts\bahnschrift.ttf", # Bahnschrift — condensed, clean
            r"C:\Windows\Fonts\calibril.ttf",   # Calibri Light
            r"C:\Windows\Fonts\calibri.ttf",    # Calibri
            r"C:\Windows\Fonts\segoeui.ttf",    # Segoe UI
        ]
        font_path = next((p for p in font_candidates if os.path.exists(p)), None)

        if font_path:
            try:
                fnt = bpy.data.fonts.load(font_path)
                txt_obj.data.font = fnt
            except Exception:
                pass

        lmat = bpy.data.materials.new(f"Label_{pname}_Mat")
        lmat.use_nodes = True
        lmat.blend_method = 'BLEND'
        lmat.show_transparent_back = False
        ln = lmat.node_tree.nodes
        ll = lmat.node_tree.links
        ln.clear()

        lout = ln.new("ShaderNodeOutputMaterial")
        lout.location = (400, 0)

        lemit = ln.new("ShaderNodeEmission")
        lemit.location = (0, 0)
        lemit.inputs["Color"].default_value = (0.85, 0.92, 1.0, 1.0)
        lemit.inputs["Strength"].default_value = 3.0
        ltrans = ln.new("ShaderNodeBsdfTransparent")
        ltrans.location = (0, 100)

        lmix = ln.new("ShaderNodeMixShader")
        lmix.location = (200, 50)
        lmix.inputs[0].default_value = 0.0

        ll.new(ltrans.outputs["BSDF"], lmix.inputs[1])
        ll.new(lemit.outputs["Emission"], lmix.inputs[2])
        ll.new(lmix.outputs["Shader"], lout.inputs["Surface"])

        txt_obj.data.materials.append(lmat)
        label_objects[pname] = {"obj": txt_obj, "mix_node": lmix}

    for idx, (pname, b_start, b_end) in enumerate(blocks):
        trans_end = b_start if idx == 0 else b_start + 40
        showcase_start = trans_end
        showcase_end = b_end

        fade_in_start = showcase_start
        fade_in_end = showcase_start + 20
        fade_out_start = showcase_end - 20
        fade_out_end = showcase_end

        mix_node = label_objects[pname]["mix_node"]

        mix_node.inputs[0].default_value = 0.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=1)
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_in_start)

        mix_node.inputs[0].default_value = 1.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_in_end)
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_out_start)

        mix_node.inputs[0].default_value = 0.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_out_end)

        if mix_node.id_data.animation_data and mix_node.id_data.animation_data.action:
            for fcurve in mix_node.id_data.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'BEZIER'

    return label_objects

# ============================================================
# SECTION 8 - CAMERA SYSTEM (orbital flyby tour)
# ============================================================
def setup_camera_rig(planets):
    """
    Builds a camera that performs a sweeping orbital flyby of each planet
    in turn. Instead of simple point-to-point dolly moves, the camera
    arcs around each subject (entry sweep -> close pass -> exit sweep)
    while a slow continuous roll and a lens "breathe" (dolly-zoom) add
    cinematic motion.
    """
    cam_focus = add_anchor("CameraFocus")
    cam_rig = add_anchor("CameraRig")

    bpy.ops.object.camera_add(location=(0, -250, 100))
    cam_obj = bpy.context.active_object
    cam_obj.name = "MainCamera"
    bpy.context.scene.camera = cam_obj
    cam_obj.parent = cam_rig

    track = cam_obj.constraints.new(type='DAMPED_TRACK')
    track.target = cam_focus
    track.track_axis = 'TRACK_NEGATIVE_Z'

    cam_data = cam_obj.data
    cam_data.lens = 50
    cam_data.clip_start = 0.01
    cam_data.clip_end = 2000
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = cam_focus
    cam_data.dof.aperture_fstop = 1.8

    sun_obj = bpy.data.objects.get("Sun")

    c_sun_rig = cam_rig.constraints.new(type='COPY_LOCATION')
    c_sun_rig.target = sun_obj
    c_sun_rig.name = "Lock_Sun"

    c_sun_focus = cam_focus.constraints.new(type='COPY_LOCATION')
    c_sun_focus.target = sun_obj
    c_sun_focus.name = "Lock_Sun"

    # Extract planet names (not full tuples) to avoid KeyError
    targets = ["Sun"] + [p[0] for p in PLANET_DATA]

    for t_name in targets:
        if t_name == "Sun":
            target_obj = bpy.data.objects.get("Sun")
        else:
            target_obj = planets[t_name]["planet"]

        cp = cam_rig.constraints.new(type='COPY_LOCATION')
        cp.target = target_obj
        cp.name = f"Lock_{t_name}"
        cp.influence = 0.0

        ct = cam_focus.constraints.new(type='COPY_LOCATION')
        ct.target = target_obj
        ct.name = f"Lock_{t_name}"
        ct.influence = 0.0

    def keyframe_lock(target_name, frame, influence):
        for obj in [cam_rig, cam_focus]:
            c = obj.constraints.get(f"Lock_{target_name}")
            if c:
                c.influence = influence
                c.keyframe_insert(data_path="influence", frame=frame)

    keyframe_lock("Sun", 1, 1.0)
    for p_name in [p[0] for p in PLANET_DATA]:
        keyframe_lock(p_name, 1, 0.0)

    # ----- Opening establishing shot - slow pull back from the Sun -----
    cam_obj.location = (0, -80, 30)
    cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.rotation_euler.z = math.radians(0)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=1)

    cam_obj.location = (0, -160, 60)
    cam_obj.keyframe_insert(data_path="location", frame=240)
    cam_obj.rotation_euler.z = math.radians(0)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=240)

    orbit_mat = bpy.data.materials.get("Orbit_Line_Mat")
    orbit_mix = orbit_mat.node_tree.nodes["OrbitFadeMix"] if orbit_mat else None

    keyframe_lock("Sun", 300, 1.0)
    keyframe_lock("Sun", 301, 0.0)

    blocks = [
        ("Mercury", 300, 420),
        ("Venus", 420, 540),
        ("Earth", 540, 660),
        ("Mars", 660, 780),
        ("Jupiter", 780, 900),
        ("Saturn", 900, 1020),
        ("Uranus", 1020, 1140),
        ("Neptune", 1140, 1260),
        ("Pluto", 1260, 1380),
    ]

    prev_target = "Sun"
    prev_end_frame = 240

    for idx, (pname, b_start, b_end) in enumerate(blocks):
        trans_start = prev_end_frame
        trans_end = b_start if idx == 0 else b_start + 40
        showcase_start = trans_end
        showcase_end = b_end

        keyframe_lock(prev_target, trans_end, 1.0)
        keyframe_lock(prev_target, trans_end + 1, 0.0)

        keyframe_lock(pname, trans_start, 0.0)
        keyframe_lock(pname, trans_end, 1.0)
        keyframe_lock(pname, showcase_end, 1.0)

        prad = planets[pname]["radius"]
        cam_prad = prad * 2.5 if pname == "Saturn" else prad

        duration = showcase_end - showcase_start
        quarter = showcase_start + duration * 0.33
        half    = showcase_start + duration * 0.66

        # Approach from the same side as hold - never cross through the sun center
        side = 1 if idx % 2 == 0 else -1
        entry_dist = cam_prad * 12.0
        hold_dist  = cam_prad * 9.0
        hold_height = cam_prad * 3.0

        # Entry stays on same side and quadrant as hold, just further out
        entry_loc = (side * entry_dist, -entry_dist, hold_height)
        hold_loc  = (side * hold_dist,  -hold_dist,  hold_height)

        cam_obj.location = entry_loc
        cam_obj.keyframe_insert(data_path="location", frame=showcase_start)

        cam_obj.location = hold_loc
        cam_obj.keyframe_insert(data_path="location", frame=quarter)

        cam_obj.location = hold_loc
        cam_obj.keyframe_insert(data_path="location", frame=showcase_end)

        # No roll - keep horizon level
        cam_obj.rotation_euler.z = math.radians(0)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=showcase_start)
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=showcase_end)

        # Fixed focal length - no zoom
        cam_data.lens = 50
        cam_data.keyframe_insert(data_path="lens", frame=showcase_start)
        cam_data.keyframe_insert(data_path="lens", frame=showcase_end)

        prev_target = pname
        prev_end_frame = showcase_end

    final_start = 1380
    final_trans_end = 1420
    final_end = 1500

    keyframe_lock(prev_target, final_trans_end, 1.0)
    keyframe_lock(prev_target, final_trans_end + 1, 0.0)

    keyframe_lock("Sun", final_start, 0.0)
    keyframe_lock("Sun", final_trans_end, 1.0)
    keyframe_lock("Sun", final_end, 1.0)

    # ----- Closing shot - straight pull back from the Sun -----
    cam_obj.location = (0, -100, 40)
    cam_obj.keyframe_insert(data_path="location", frame=final_trans_end)
    cam_obj.rotation_euler.z = math.radians(0)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=final_trans_end)

    cam_obj.location = (0, -220, 90)
    cam_obj.keyframe_insert(data_path="location", frame=final_end)
    cam_obj.rotation_euler.z = math.radians(0)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=final_end)

    cam_data.lens = 50
    cam_data.keyframe_insert(data_path="lens", frame=final_end)

    for obj in [cam_rig, cam_focus, cam_obj]:
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'BEZIER'

    # No camera shake - keep it smooth and stable

    return cam_obj, blocks

# ============================================================
# MAIN
# ============================================================
def launch():
    print("=== Solar System Generator - Blender 3.6 ===")
    print("[1/5] Setting up scene...")
    build_environment()

    print("[2/5] Building planets and materials...")
    planets = build_system()

    print("[2b/5] Drawing orbit lines...")
    render_orbit_lines()

    print("[2c/5] Scattering asteroids...")
    place_debris()

    print("[3/5] Animating orbits and rotations...")
    run_motion(planets)

    print("[4/5] Building camera animation...")
    cam_obj, blocks = setup_camera_rig(planets)

    print("[5/5] Adding planet labels...")
    add_name_tags(planets, cam_obj, blocks)

    print("Finalising scene...")
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    print("=== Done! Press SPACE or render to see the animation. ===")

launch()