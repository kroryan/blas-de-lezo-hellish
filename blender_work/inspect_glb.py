import bpy, os, sys, math
from mathutils import Vector
src = sys.argv[sys.argv.index('--') + 1]
out = sys.argv[sys.argv.index('--') + 2]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
for o in bpy.data.objects:
    print('OBJ', o.name, o.type, tuple(round(x, 3) for x in o.dimensions), o.data.name if o.data else None)
    if o.type == 'MESH':
        print('  verts', len(o.data.vertices), 'tris', sum(len(p.vertices) - 2 for p in o.data.polygons),
              'uv', len(o.data.uv_layers), 'colattr', [a.name for a in o.data.color_attributes],
              'mats', [m.name for m in o.data.materials])
    if o.type == 'ARMATURE':
        print('  bones', len(o.data.bones))
for im in bpy.data.images:
    print('IMG', im.name, tuple(im.size))
for m in bpy.data.materials:
    if m.node_tree:
        print('MAT', m.name, [n.type for n in m.node_tree.nodes])
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
print('BOUNDS', tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 700; sc.render.resolution_y = 900
c = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', c); sc.collection.objects.link(co); sc.camera = co
c.type = 'ORTHO'; size = hi - lo; c.ortho_scale = max(size) * 1.1
ctr = (lo + hi) / 2; r = max(size) * 3
for n, d in [('front', (0, -1, 0)), ('back', (0, 1, 0)), ('left', (1, 0, 0)), ('right', (-1, 0, 0)), ('top_front', (0, -1, 0.3))]:
    co.location = ctr + Vector(d).normalized() * r
    co.rotation_euler = (ctr - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(out, n + '.png'); bpy.ops.render.render(write_still=True)
